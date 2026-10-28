# 第 7 课验证记录

## 范围

- 变更：`2026-10-28-lesson-07-completion`
- 基线提交：`e42b902`
- 日期：2026-10-28
- 环境：Python 3.12.3、Flask 3.1.2、Gunicorn 23.0.0、OpenSpec 1.13.0

本记录验证外部配置、单行 JSON 日志、界面状态、写接口幂等声明、四条失败路径、工程规范、
OpenSpec 严格校验和本地启动。真实 Docker、模型和跨成员机器评审另列。

## 自动化门禁

执行：

```bash
make check
```

结果：

- Ruff 静态检查与格式检查通过；
- Python 编译通过；
- Pytest：`37 passed`；
- SQL 与 `sqlite3` 导入分层检查通过；
- 当前文件和历史密钥扫描通过；
- 历史归档检查通过；
- OpenSpec 新变更 `--strict` 通过；
- OpenSpec 历史归档 `--strict` 通过。

## 进程冒烟

使用临时数据库和全部外部配置执行 `make run`，结果：

- `/health` 返回 200、`code=0`、`database=ok`；
- 随请求提交的 `X-Request-ID: lesson07-make-run` 与 JSON 日志字段一致；
- `student-a` 登录返回 200、`code=0`、`class-a`、`student`；
- Gunicorn 启动、请求、错误和停机日志全部为单行 JSON；
- 独立 Gunicorn 冒烟中非 JSON 日志行数为 0；
- 缺少 `FLASK_SECRET_KEY` 时进程以退出码 1 失败，并明确指出缺失键。

## 分支保护

GitHub API 已确认 `main` 受保护，详见 `branch-protection.md`。

## 尚未验证

- WSL 未启用 Docker Desktop 集成，无法执行镜像构建和 Compose 运行；
- 没有可用 `GLM_API_KEY`，10 条评测集未调用真实模型；
- 尚未完成另一成员在自己机器上的从零启动和交叉评审；
- 尚未完成首次回滚演练；
- 因交叉评审未完成，本次变更暂不归档，也暂不打骨架标签。
