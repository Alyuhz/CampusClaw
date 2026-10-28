---
name: campusclaw-change-data
description: Plan and verify a CampusClaw SQLite schema or data change with migration, rollback, class ownership, and deletion checks; use for db.py and data dictionary changes.
---

# CampusClaw：按规范做数据变更

先读 `.cursor/rules/data.mdc`、`docs/data-dictionary.md`、
`campusclaw/db.py` 和当前变更规约。

1. 明确结构变化、数据影响、班级归属和回滚动作。
2. 迁移只增不改、可重复执行，并保持旧代码可运行；禁止直接修改已发布迁移。
3. 同步数据字典、API 文档和相关测试。
4. 删除能力必须列出业务表、FTS 索引、外部文件、缓存与备份副本。
5. 先在临时数据库和 A/B 两班测试数据上执行迁移与回滚；运行 `make check`。
6. 生产迁移、恢复或删除数据前先确认精确目标和备份，并获得用户明确授权。

任何不可逆或没有演练过的迁移都应停止实施。
