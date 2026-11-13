
# CampusClaw

> 面向班级教学场景的智能知识库与学习助手

CampusClaw 是一个基于 Flask 和 RAG（检索增强生成）技术开发的 Web 应用，面向教师与学生提供课程资料管理、班级知识检索和智能问答服务。

系统以班级课程资料为知识来源，结合全文检索与大语言模型生成回答，并提供引用来源，帮助学生快速查找和理解课程知识，同时支持班级级别的数据隔离与权限管理。

## 当前完成状态

仓库已从“只有项目说明”补齐为可运行骨架：

- 登录、退出与令牌吊销；
- 教师上传 Markdown/TXT、自动切片与本班范围 FTS5 索引；
- 本班资料列表、详情和关键词检索；
- 带真实切片的问答；无依据时拒绝生成引用；
- 可选智谱 GLM 调用，未配置 Key 时使用确定性抽取式回答并标记降级；
- 免认证 `/health`、统一错误结构、请求标识与单行 JSON 日志；
- Pytest 接口/单元测试、Ruff、布局检查、密钥扫描和变更规约校验；
- Dockerfile、Compose、健康检查、CI 与 Git 提交前钩子。

2026-11-11 已完成本地容器构建、健康与非 root/镜像层检查；真实 GLM 调用仍需测试凭证。

## 一、核心功能

### 1. 用户与班级管理

- 支持教师、学生两类用户登录
- 根据用户身份和所属班级控制访问权限
- 不同班级的资料、检索结果和问答依据相互隔离

### 2. 课程资料管理

- 支持教师上传和查看课程资料
- 支持 Markdown、TXT 等文本格式
- 自动提取文本、切分知识片段并建立检索索引

### 3. 班级知识检索

- 基于 SQLite FTS5 实现全文检索
- 支持关键词查询课程资料
- 返回相关原文片段、资料来源及行号
- 检索结果按相关度排序

### 4. 智能知识问答

- 基于 RAG 技术实现课程知识问答
- 使用课程资料作为大语言模型的参考内容
- 回答附带引用来源，便于核验
- 当知识库缺少相关内容时给出提示，减少无依据的回答

## 二、技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python、Flask |
| 前端 | HTML、CSS、JavaScript |
| 数据库 | SQLite |
| 全文检索 | SQLite FTS5 |
| 智能问答 | RAG、智谱 GLM API |
| 身份认证 | JWT、Bearer Token |
| 自动化测试 | Pytest |
| 部署 | Docker Compose |

## 三、本地运行

### 1. 准备配置

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

- `FLASK_SECRET_KEY`、`JWT_SECRET_KEY`：两段不同的随机长字符串；
- `SEED_TEACHER_PASSWORD`、`SEED_STUDENT_PASSWORD`：本地演示账号口令；
- `DATABASE_PATH=instance/campusclaw.sqlite3`；
- `GLM_API_KEY`：可留空，应用将使用抽取式回答。

缺少必需配置时应用会直接启动失败，不会使用默认密钥。

### 2. 安装依赖

```bash
make setup
```

`make setup` 使用 `uv` 创建 `.venv`、安装开发依赖并尝试启用仓库钩子。也可在支持
`ensurepip` 的环境中自行执行：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.lock
```

### 3. 启动

```bash
make run
```

访问 <http://127.0.0.1:5000/>，健康检查为 <http://127.0.0.1:5000/health>。

开发演示账号：

- `teacher-a`、`student-a`：属于 `class-a`；
- `teacher-b`、`student-b`：属于 `class-b`；
- 口令分别取自 `SEED_TEACHER_PASSWORD` 与 `SEED_STUDENT_PASSWORD`。

### 4. 容器启动

安装 Docker 后执行：

```bash
docker compose up --build -d
curl --fail http://127.0.0.1:5000/health
```

若修改了 `WEB_PORT`，请同步替换访问端口。

## 四、系统工作流程

1. 教师登录系统并上传课程资料。
2. 系统提取资料正文，切分知识片段并建立全文检索索引。
3. 学生登录后输入课程相关问题。
4. 系统根据用户所属班级检索相关知识片段。
5. 配置模型 Key 时由大语言模型结合检索结果生成回答；否则使用确定性抽取式回答。
6. 系统返回回答及引用来源，供学生查看和核验。

## 五、后续扩展计划

### 1. 多格式资料处理

- 增加 PDF、Word 文档的文本提取与索引
- 支持课程主题、章节等分类信息
- 支持资料预览、更新及索引同步重建

### 2. 检索与问答体验优化

- 支持按资料名称、章节和上传时间组合筛选
- 支持查看引用片段上下文及原文定位
- 增加答案反馈功能

### 3. 学习辅助功能

- 根据课程资料生成知识点摘要和复习提纲
- 自动生成自测题
- 支持收藏重点资料和问答结果
- 记录自测结果与错题

### 4. 教学统计与管理

- 统计热门检索词和常见问题
- 分析课程资料访问情况
- 通过图表展示班级知识点关注度
- 仅展示班级范围内的汇总数据

以上功能将根据项目开发进度逐步实现。

## 六、测试与部署

一条命令执行全部门禁：

```bash
make check
```

门禁依次检查 Ruff 格式与静态规则、Python 编译、Pytest、SQL 分层、密钥扫描与归档变更
规约。任一子项非零退出即失败。

接口测试覆盖登录、退出、角色限制、跨班访问、伪造班级参数、检索隔离、带出处回答、
无依据拒绝和上传格式；跨班与不存在资料的 404 响应体逐字节比较。

部署使用多阶段 Dockerfile 与 Compose，并提供 `/health` 健康检查。发布前必须记录版本、
验证结论与回滚步骤；具体规则见 `.cursor/rules/ops.mdc` 和 `docs/operations.md`。

## 七、接口与工程资产

主要 API：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查，无需认证 |
| POST | `/api/v1/auth/login` | 登录并获取 Bearer token |
| POST | `/api/v1/auth/logout` | 吊销当前会话 |
| GET | `/api/v1/me` | 当前用户与班级 |
| GET | `/api/v1/materials` | 本班资料列表 |
| POST | `/api/v1/materials` | 教师上传本班资料 |
| GET | `/api/v1/materials/{id}` | 本班资料详情与切片 |
| GET | `/api/v1/search?q=` | 本班资料检索 |
| POST | `/api/v1/ask` | 带真实出处回答 |

工程资产：

- `AGENTS.md`：常驻工程约束与完成定义；
- `.cursor/rules/`：产品、后端、安全、测试、运维、AI、数据与评审规范；
- `openspec/changes/archive/`：已归档的四份变更规约与场景；
- `skills/`：按场景执行的 Codex 技能；
- `docs/`：API、数据字典、运行维护与验证记录；
- `tests/`：自动化回归用例；
- `Makefile`、`Dockerfile`、`compose.yaml`：本地与容器入口。

## 八、项目说明

本项目为课程小组实践项目，基于已有班级知识库原型进行功能完善与扩展。

项目重点在于将课程资料管理、全文检索和大语言模型问答相结合，实现具有来源追溯能力和班级数据隔离机制的智能学习辅助系统。

当前未选择开源许可证；对外发布或复用前需由项目组明确许可方式。


## 第 9 课安全验证

[交付索引与前后对照](docs/changes/2026-11-11-lesson09-security-red-to-green.md) 汇总实现、回归与外部待办。

.env.example 只列键名空值；本地至少填写 APP_VERSION、DATABASE_PATH、FLASK_SECRET_KEY、JWT_SECRET_KEY（至少32字节）和两类种子口令。HTTP 开发另填 COOKIE_SECURE=false；HTTPS 生产默认 true。可选模型及数值配置空值使用已声明默认值。

依赖安装后，浏览器测试优先使用本机 Google Chrome；其他位置可设 CHROME_EXECUTABLE。没有 Chrome 时执行 `python -m playwright install chromium` 安装 Playwright 官方浏览器。CI 安装 Chromium 及系统依赖。

```bash
make check
make check-security
```

make check 已包含 apitest/cases/ 的 SQL、真实 DOM XSS 与跨站 CSRF 回归。make check-security 对当前工作树/本地可见 Git 历史做秘密格式扫描，并审计运行与开发锁文件；任何未登记漏洞、无效例外或审计不可达非零退出。漏洞例外格式见 reports/security-baseline.md，当前 security-exceptions.json 为空。

认证写请求新增一次性 CSRF 令牌和绑定 Cookie；现有页面已适配，命令行客户端须保留 Cookie 并在每次写前取令牌，详见 docs/api.md。只读教师审计查询限定本班。

具备 Docker 时可重跑镜像验证（临时随机配置与容器会自动清理）：

```bash
docker build -t campusclaw:lesson09-security .
.venv/bin/python scripts/verify_image.py
```

第九课验证时工作区尚未提交；现已整理为本地提交，仍未推送，见[提交索引](reports/submission-commits.md)；真实模型实验与另一组员独立复核仍需外部条件，缺失的异步/评分/技能/向量功能未被计为课程通过。

## 第十课交付与验证

本课采用 SQLite/FTS5 与同步上传、检索、问答方案。原课堂异步四步与批改技能的差异见 [盘点](reports/commands.md)；完整结论与证据从 [report.md](report.md) 打开。

前置条件：Docker Engine 与 Compose v2（支持 environment secrets），本机 Python 3.12 用于门禁及验证脚本，官方依赖见锁文件。浏览器测试使用本机 Chrome 或 Playwright 官方 Chromium。首次运行先按上文复制并填写 `.env`，其中 `DATABASE_PATH=instance/campusclaw.sqlite3`、本地 HTTP 的 `COOKIE_SECURE=false`；容器卷对应此数据库位置。随后一条命令构建并启动：

```bash
docker compose up --build -d --wait
```

`/health` 保留原健康合同，`/ready` 检查数据库必要表及迁移，故障返回503，容器据此接流量。应用以非root、双worker运行；最终镜像保留业务字节码与资源，不含业务 `.py`，第三方运行库可能含Python源码。配置、凭证和数据库不进镜像。数据在命名卷中，普通 `docker compose down` 保留，`down -v` 会删除。

检索缓存默认关闭，填写 `SEARCH_CACHE_ENABLED=true` 启用256项/30秒缓存；键含班级与数据库版本，教师上传与版本递增同事务，其他worker下一请求读取新版本。

可选观测：在 `.env` 配置 `TELEMETRY_ENABLED=true`、至少32字节的独立 `METRICS_TOKEN`、非空 `GRAFANA_ADMIN_PASSWORD`。执行：

```bash
docker compose --env-file .env --profile telemetry up --build -d --wait
```

Grafana `http://127.0.0.1:3000`，账号admin、口令取自配置；Prometheus为9090，Alertmanager为9093。全部默认绑定回环地址，端口冲突可设置 `WEB_PORT`、`GRAFANA_PORT`、`PROMETHEUS_PORT`、`ALERTMANAGER_PORT`。三个capability分别为materials-upload、knowledge-search、grounded-ask。面板三组为调用量、计数计算的错误率、P95与执行中请求。执行中请求lease不代表任务队列。告警接收器为本地实验渠道，外部通知需另行配置。

```bash
make check
make check-security
make image
.venv/bin/python -m scripts.verify_delivery --alerts
.venv/bin/python -m scripts.verify_workers
.venv/bin/python -m scripts.verify_lease_crash
.venv/bin/python -m scripts.verify_mobile
.venv/bin/python -m scripts.bench
.venv/bin/python -m scripts.analyze_bench
```

双门禁任一非零均失败。安全门禁会访问官方漏洞数据库，网络不可达也失败。容器验证脚本使用干净临时目录、随机配置与独立卷，完成后只清理自己的资源；移动脚本需本机Chrome。压测固定种子0，两班各200资料×20片段，2 worker×4线程，并发1/4/8/16/32，预热5秒、测量20秒、3次重复、缓存关/开共90组合，约40分钟，使用合成数据和本地模型替身；详细参数见 `python -m scripts.bench --help`。压测结果归档后请先备份再重跑，脚本会更新本课结果文件。

`make image` 对未提交源码生成工作区摘要标签与 `reports/lesson10/build.json`，不能将脏工作区标成已有提交。CI依次运行同样的双门禁与构建，产物含来源元数据及镜像tar；实际远端运行编号、主干保护和真实提交对应关系仍待维护者执行。

手机同源访问需部署可信HTTPS并配置窄范围网络入口；本地移动视口自动化不是实机证据。当前不开放跨域，不应通过宽泛CORS或关闭CSRF实现手机访问。
