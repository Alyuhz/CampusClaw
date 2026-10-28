---
name: campusclaw-review
description: Review a CampusClaw change against its scenarios, engineering rules, and release evidence; use for code review, completion checks, and pre-merge audits.
---

# CampusClaw：评审一次变更

先读 `AGENTS.md`、对应 `.cursor/rules/*.mdc`、变更四份文件与验证记录。

按以下顺序给出有证据的结论：

1. 需求：每条能力是否有场景，场景是否有前置条件、操作和可观测结果。
2. 安全：班级是否只取自服务端用户记录；跨班与不存在是否返回一致 404；
   外部内容是否始终按数据处理。
3. 数据：SQL 是否只在 `db.py`；迁移是否可逆、字典是否同步。
4. 测试：失败路径与边界是否覆盖；改坏业务逻辑时测试是否会红。
5. 运维：配置是否外置；日志是否结构化且无敏感值；健康检查与回滚是否可验证。
6. 门禁：运行 `make check`，核对 `Change`、`Verify`、`Evidence` 三字段。

评审请求只做审查时不修改代码。按严重程度报告缺陷，并引用具体文件与行；没有证据的猜测不列为缺陷。
