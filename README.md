
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

本地验证机器未安装 Docker，因此容器构建和真实 GLM 调用仍需在具备相应环境与 Key 的机器上
完成最终联调；其余代码、接口与门禁可在本机执行。

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

编辑 `.env`，填写示例中的全部空值：

- `FLASK_SECRET_KEY`、`JWT_SECRET_KEY`：两段不同的随机长字符串；
- `SEED_TEACHER_PASSWORD`、`SEED_STUDENT_PASSWORD`：本地演示账号口令；
- `DATABASE_PATH=instance/campusclaw.sqlite3`；
- `APP_VERSION`、`WEB_PORT`、`GLM_MODEL`、`GLM_TEMPERATURE`、`GLM_TIMEOUT_SECONDS`、
  `MAX_UPLOAD_BYTES`、`TOKEN_TTL_SECONDS`、`SEARCH_RESULT_LIMIT`：显式填写运行值；
- `GLM_API_KEY`：唯一允许留空的键；为空时应用使用抽取式回答。

代码不提供配置默认值。除 `GLM_API_KEY` 外，任一键缺失或为空时应用都会直接启动失败。

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

仓库使用 OpenSpec 1.13 做严格规约校验。运行 `make check` 前需在 PATH 中提供
`openspec`，例如：

```bash
npm install --global @fission-ai/openspec@1.13.0
```

### 3. 启动

```bash
make run
```

启动使用 Gunicorn 和 `.env` 中的 `WEB_PORT`。访问 <http://127.0.0.1:5000/>，
健康检查为 <http://127.0.0.1:5000/health>（端口以本机配置为准）。

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

门禁依次检查 Ruff 格式与静态规则、Python 编译、Pytest、SQL 与导入分层、密钥扫描、
历史变更检查和 OpenSpec `--strict` 校验。任一子项非零退出即失败。

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
- `docs/lesson-07/`：第 7 课规约追踪、验证与交叉评审记录；
- `tests/`：自动化回归用例；
- `Makefile`、`Dockerfile`、`compose.yaml`：本地与容器入口。

## 八、项目说明

本项目为课程小组实践项目，基于已有班级知识库原型进行功能完善与扩展。

项目重点在于将课程资料管理、全文检索和大语言模型问答相结合，实现具有来源追溯能力和班级数据隔离机制的智能学习辅助系统。

当前未选择开源许可证；对外发布或复用前需由项目组明确许可方式。
