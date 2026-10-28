---
name: campusclaw-release
description: Prepare, verify, and record a CampusClaw release or rollback; use for version tags, container releases, and deployment evidence.
---

# CampusClaw：按规范发一次版本

先读 `docs/operations.md`、`.cursor/rules/ops.mdc` 和
`openspec/changes/archive/` 中最新的变更。

1. 运行 `make check`；失败即停止。
2. 确认版本号、提交号和上一版本标签都存在。
3. 备份 SQLite 数据库并记录备份位置；不得把数据文件提交到 Git。
4. 构建镜像并按提交号打标签；不得使用 `latest` 作为唯一标签。
5. 在测试环境启动，等待 `/health` 返回 2xx，再记录验证结论。
6. 将版本、变更、验证和回滚命令写入 `docs/releases/`。
7. 只有获得明确的发布授权后才操作生产环境。生产变更或删除数据前必须先确认目标与回滚点。

回滚只回到上一版本标签。未演练的回滚不算可用。
