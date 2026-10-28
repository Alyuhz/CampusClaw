---
name: campusclaw-add-tests
description: Add CampusClaw tests that trace to archived scenarios and verify class-isolated behavior; use after implementing or fixing a capability.
---

# CampusClaw：按规范补测试

先读 `AGENTS.md`、`.cursor/rules/testing.mdc` 和本次变更的
`specs/*/spec.md`。

1. 为每个新增场景建立“规约场景 → 测试函数”的对应关系。
2. 每个资源读写场景同时覆盖跨班访问；跨班与不存在响应必须比较完整响应字节。
3. 断言业务值、数据变化、引用真实性和权限结果，不只断言非空或无异常。
4. 使用临时 SQLite 数据库；测试不访问真实 GLM 服务。
5. 修复缺陷时，先写一个在修复前会失败的回归用例。
6. 运行 `make test` 和 `make check`；失败时修代码或测试，不跳过、不删除失败断言。

若规约缺少可观测结果，先补规约，不凭空猜测验收条件。
