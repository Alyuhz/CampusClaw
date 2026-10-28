## Context

见 `proposal.md` 的 Why。当前 Flask 应用已经能完成班级隔离的资料检索与问答，但配置、
日志和界面分别存在默认值、重复输出与状态缺失。OpenSpec 目录有历史变更，却没有原生
项目配置和严格校验链路。

## Goals / Non-Goals

**Goals:**

- 用一套可执行门禁证明配置外置、单行 JSON 日志、四状态界面和四条失败路径。
- 保持现有 API 路径、响应结构和班级授权模型不变。
- 让第 7 课验证记录可以从变更名直接检索。

**Non-Goals:**

- 不实现服务端幂等键、上传去重、Docker 实机联调或真实 GLM 质量评测。
- 不修改已归档 `class-material-search` 的历史内容。
- 不把另一成员机器上的交叉评审或 GitHub 保护规则伪造成本地已通过。

## Decisions

1. **所有应用配置必填，GLM Key 仍可空。** 使用 `.env` 显式提供模型、限额和超时，
   避免同一份镜像因代码默认值产生隐式差异。代价是升级时必须补齐新键。
2. **应用请求日志作为唯一请求访问日志。** 关闭 Werkzeug 访问日志和 Gunicorn access
   log，由 `after_request` 输出带 `request_id` 的 JSON。Gunicorn error log 使用同一
   JSON formatter，保留启动与进程故障信息。
3. **幂等性通过契约声明，不以 UI 锁冒充。** 登录、上传和问答明确为非幂等，退出声明
   为副作用幂等；前端提交锁只防止用户误触，不承担服务端去重。
4. **SQL 异常在数据层转换为空命中。** `search.py` 只调用数据层函数，不导入
   `sqlite3`，由 `db.py` 决定 FTS 不可用时是否允许 LIKE 回退。
5. **原生 OpenSpec 校验与项目专用检查并存。** OpenSpec 负责严格结构和依赖，
   `validate_change.py` 继续检查历史归档与课程要求的补充约束。

## Risks / Trade-offs

- [升级时缺少新必填配置导致启动失败] → README 列出全部键，并增加逐键失败测试。
- [关闭框架访问日志可能降低排障信息] → 应用 JSON 日志保留方法、路径、状态和耗时。
- [非幂等上传仍可能被脚本重复调用] → 在 API 文档显式声明；后续需要时另立幂等键变更。
- [真实 Docker、模型和跨人评审当前不可执行] → 验证记录保持未通过状态，不创建最终标签。

## Migration Plan

1. 在部署机的 `.env` 中补齐 `.env.example` 的全部键。
2. 运行 `make check` 和本地进程冒烟。
3. 通过新分支和评审合并；若失败，恢复旧提交并回填旧配置。

## Open Questions

无。
