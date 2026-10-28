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
