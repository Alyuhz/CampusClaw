# CampusClaw 数据字典

数据库为单文件 SQLite。时间统一使用 UTC ISO 8601 字符串；业务资源必须携带
`class_id`。所有 SQL 位于 `campusclaw/db.py`。

结构迁移位于 `campusclaw/migrations/`，文件名按版本排序。`schema_migrations` 记录已执行
迁移；迁移文件发布后只增不改。

## schema_migrations

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| version | TEXT | PK | 迁移文件名 |
| applied_at | TEXT | NOT NULL | 执行时间 |

## users

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| id | INTEGER | PK | 用户内部标识 |
| username | TEXT | UNIQUE, NOT NULL | 登录账号 |
| password_hash | TEXT | NOT NULL | 加盐单向口令哈希 |
| role | TEXT | teacher / student | 功能角色 |
| class_id | TEXT | NOT NULL | 用户所属班级 |
| created_at | TEXT | NOT NULL | 创建时间 |

## auth_sessions

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| jti | TEXT | PK | JWT 唯一会话标识 |
| user_id | INTEGER | FK users | 会话所属用户 |
| expires_at | TEXT | NOT NULL | 过期时间 |
| created_at | TEXT | NOT NULL | 登录时间 |
| revoked_at | TEXT | NULL | 吊销时间；非空后令牌立即失效 |

## materials

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| id | INTEGER | PK | 资料标识 |
| class_id | TEXT | NOT NULL | 资料所属班级 |
| title | TEXT | NOT NULL | 用户可见标题 |
| filename | TEXT | NOT NULL | 服务端生成的安全文件名 |
| created_by | INTEGER | FK users | 上传教师 |
| created_at | TEXT | NOT NULL | 上传时间 |

## chunks

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| id | INTEGER | PK | 切片标识 |
| material_id | INTEGER | FK materials | 所属资料 |
| class_id | TEXT | NOT NULL | 冗余班级字段，用于逐资源授权 |
| chunk_index | INTEGER | 与 material 联合唯一 | 资料内顺序 |
| content | TEXT | NOT NULL | 切片正文 |
| start_line | INTEGER | NOT NULL | 原文起始行，从 1 开始 |
| end_line | INTEGER | NOT NULL | 原文结束行 |

## chunks_fts

FTS5 虚拟表，`rowid` 对应 `chunks.id`，内容为切片正文，使用 trigram 分词。

## 敏感数据与留存

| 级别 | 数据 | 处理 |
|---|---|---|
| 内部 | 班级、标题 | 仅本班可见 |
| 敏感 | 资料正文、切片 | 不进入日志；仅本班检索/详情返回 |
| 个人信息 | 账号、问题、会话 | 不进入日志；当前版本不持久化问题原文 |

当前版本不提供删除接口。实现删除能力时必须同步清理 `materials`、`chunks`、
`chunks_fts`、外部文件与备份，并执行 A/B 两班删除演练。


## 002_security 迁移

迁移仅新增表，版本发现和 DDL 由 BEGIN IMMEDIATE 串行保护，避免两个 worker 同时首次建表；可重复执行。回滚前备份数据库并确认前后端同版本；保留审计表可支持旧应用回滚。

### csrf_tokens（敏感身份辅助数据）

| 字段 | 含义 |
|---|---|
| token_hash TEXT PK | 一次性令牌 SHA256，不存原始值 |
| jti TEXT NOT NULL FK auth_sessions | 绑定服务端会话 |
| binding_hash TEXT NOT NULL | 浏览器绑定随机值 SHA256 |
| expires_at TEXT NOT NULL | UTC 到期时间，签发后10分钟 |
| used_at TEXT nullable | 原子消费时间，非空不可重放 |

### operation_logs（内部审计数据）

| 字段 | 含义 |
|---|---|
| id INTEGER PK | 稳定分页兜底键 |
| event_id TEXT UNIQUE NOT NULL | 服务端生成，防同请求重复审计，不采信客户端去重 ID |
| class_id TEXT NOT NULL | 服务端班级；无身份失败用空字符串，不向班级教师泄露其他班日志 |
| actor_id INTEGER nullable | 已确认的操作人，匿名为 null |
| created_at TEXT NOT NULL | UTC 审计时间 |
| payload TEXT NOT NULL | CHECK(json_valid) 单行 JSON，七列语义见 API 文档 |

索引：(class_id,created_at,id)、(actor_id,created_at)。payload 不含认证头、Cookie 值、口令、密钥、资料/问题正文。无技能时标明原因，未知用量 null，不伪造 0 用量。对象截断512字符，事件上限8192字节。

完整结构回滚动作：备份后 DROP TABLE csrf_tokens、DROP TABLE operation_logs，并删除 schema_migrations 中 002_security.sql 对应版本行，才能允许日后重新迁移。应用回滚通常保留新增表，避免丢审计数据；实际备份恢复/重复与并发迁移测试见 tests/test_security.py。

当前不存模型密钥字段；password_hash 为单向口令哈希，不是可解密模型凭证。以后若引入凭证存储，需单独定义加密与外置解密口令。

## 第十课交付与验证

迁移003_delivery.sql只增表，当前处于扩与迁，无缩阶段，不删除旧字段。上线前备份SQLite一致性快照，回退应用时保留新增表，数据恢复须从备份验证，禁止运行中删除数据库。

| 表 | 键与字段 | 不变量 |
|---|---|---|
| class_revisions | class_id主键、revision整数 | 成功上传与版本递增同事务；历史班级缺行按0处理 |
| metric_totals | capability/status复合主键，n、sum_seconds、buckets(JSON) | 仅固定能力标签，计数跨worker与重启保留 |
| metric_receipts | event_id主键，关联operation_logs | 相同事件终结重试不重复计数 |
| request_leases | event_id主键、capability、expires；expires索引 | 正常结束删除，运行续约，异常后过期；与业务行无关 |

HTTP操作日志终结、指标聚合、去重收据与lease删除在同一数据库事务；业务写入与审计成功/班级版本是另一服务事务，HTTP终结不与业务事务或外部模型构成跨系统原子性。参见 [事务三查](../reports/risk-transaction.md)。指标表与收据需随审计保留策略统一维护，不能单独清收据后重放旧事件。
