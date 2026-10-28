# 项目完成状态

更新日期：2026-10-28

## 四步基线

| 步骤 | 状态 | 证据 | 尚缺 |
|---|---|---|---|
| 建仓库 | 基本完成 | README、忽略规则、协作文档、密钥边界、提交前脚本 | 用户复核后提交；远端分支保护需在 GitHub 设置 |
| 定规约 | 完成初版 | `openspec/changes/archive/2026-10-28-class-material-search/` 四份文件与 10 个场景 | 后续变更继续新增规约，不改历史 |
| 立规范 | 完成初版 | `AGENTS.md`、8 份 `.cursor/rules/`、5 个项目技能 | Harness 若只从用户级目录发现技能，需要把 `skills/` 加入其技能路径 |
| 落骨架 | 本地完成 | Flask 纵向切片、`/health`、日志、配置外置、迁移、测试、`make check`、Docker/Compose | Docker 构建与真实 GLM Key 联调受本机环境限制 |

## 本地可验证

```bash
make setup
make check
make run
```

`make check` 当前结果：19 个测试通过；Ruff、格式、编译、SQL 分层、密钥扫描和变更规约
校验全部通过。

## 外部环境待办

1. 用户评审工作区改动，确认后创建提交；
2. 在具备 Docker 的机器执行 `docker compose up --build -d` 和健康检查；
3. 提供测试用 `GLM_API_KEY` 后运行 `evals/cases.jsonl`，记录模型质量与用量；
4. 完成首次回滚演练，记录耗时；
5. 创建版本标签，例如 `v0.1.0`。

本工作区 `.git` 为只读，无法由助手创建提交、标签或写入
`git config core.hooksPath .githooks`；钩子文件已入库，具备写权限后可启用。
