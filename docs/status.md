# 项目完成状态

更新日期：2026-10-28

## 四步基线

| 步骤 | 状态 | 证据 | 尚缺 |
|---|---|---|---|
| 建仓库 | 已完成 | README、忽略规则、协作文档、密钥边界、提交前脚本 | 首次提交未包含 `.gitignore`，该历史缺口无法重写补齐 |
| 定规约 | 已完成 | 历史规约、OpenSpec 配置、原生 `--strict` 校验与新变更 | 无 |
| 立规范 | 已完成 | `AGENTS.md`、8 份 `.cursor/rules/`、5 个项目技能、课件判据 | Harness 若只从用户级目录发现技能，需要把 `skills/` 加入其技能路径 |
| 落骨架 | 本地完成 | Flask 应用、`/health`、单行 JSON 日志、全外部配置、测试、Docker/Compose | Docker 实机构建与真实 GLM Key 联调待外部环境 |

## 本地可验证

```bash
make setup
make check
make run
```

`make check` 当前结果：33 个测试通过；Ruff、格式、编译、SQL 分层、密钥扫描、历史变更
检查与 OpenSpec `--strict` 全部通过。

## 外部环境待办

1. 在具备 Docker 的机器执行 `docker compose up --build -d` 和健康检查；
2. 提供测试用 `GLM_API_KEY` 后运行 `evals/cases.jsonl`，记录模型质量与用量；
3. 完成首次回滚演练，记录耗时；
4. 由组内另一成员从其机器从零启动并完成交叉评审；
5. 评审通过后归档本次变更并创建第 7 课骨架标签。

最新状态与证据见 `docs/lesson-07/`。
