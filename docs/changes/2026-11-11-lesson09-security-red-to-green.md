# 第九课本地交付索引

日期：2026-11-11。状态：本地可执行检查与当前项目安全修复完成；全部修改未提交、未推送。基线 e42b902，实际被测版本由 [工作区摘要](../../reports/evidence/source-manifest.json) 标识。

## 实际验证

| 检查 | 结果 | 证据 |
|---|---|---|
| 原功能+新增安全回归 | make check 退出0，51 passed | [完整输出](../../reports/evidence/make-check-final.txt) |
| SQL/XSS/CSRF 三件套 | 4 用例通过，真实浏览器 DOM/跨站 | [专项输出](../../reports/evidence/injection-final.txt)、[DOM](../../reports/evidence/xss-dom.html)、[跨站](../../reports/evidence/csrf-cross-site.json) |
| 依赖与秘密门禁 | 退出0、未处置0、例外0 | [门禁输出](../../reports/evidence/check-security-final.txt)、[最终审计](../../reports/evidence/dependencies-current.json) |
| 先红后绿 | 隔离合成风险退出2→0 | [门禁记录](../../reports/gate-red-green.md) |
| 镜像与数据恢复 | health ok、UID10001、10层无匹配；备份/迁移测试通过 | [镜像证据](../../reports/evidence/docker-verification.json)、tests/test_security.py |
| 同步演示 | 登录200→上传201→本班检索/问答200→跨班同体404 | [机器记录](../../reports/evidence/demo.json) |
| OpenSpec 严格校验 | 文档最终核验时记录 | 当前变更目录及校验记录 |

## 能力—场景—证据

| 能力 | 场景 | 报告/用例 |
|---|---|---|
| security-access-boundaries | SEC-01 默认身份矩阵；SEC-02 双检索/同体404；SEC-03 无残留；SEC-04 事务写授权 | [前后对照](../../reports/security-fix-log.md)、tests/test_security.py |
| security-injection-regression | SQL、实际 DOM、CSRF 令牌/Cookie/跨站/重放 | [SQL](../../apitest/cases/sql-injection.md)、[XSS](../../apitest/cases/xss.md)、[CSRF](../../apitest/cases/csrf.md)、apitest/cases/test_injection.py |
| security-asset-gates | SEC-05 历史扫描与镜像；SEC-06 锁文件升级/例外/不可达 | [基线](../../reports/security-baseline.md)、[门禁红绿](../../reports/gate-red-green.md)、tests/test_security_gate.py |
| security-audit-evidence | SEC-07 七列/拒绝/查询/故障；SEC-08 四步恶意替身 | [实验](../../reports/sec08-experiment.md)、[复盘](../../reports/rework.md)、tests/test_sec08.py |

评审：[脚本输出](../../reports/review-02.md)、[AI 规则自审](../../reports/review-03.md)、[另一组员待执行](../../reports/review-04.md)。版本状态：[本地工作区](../../reports/commits.md)。

## 仍需外部条件

真实模型没有测试凭证，替身实验不能冒充真实模型反应；另一组员还需独立机器从零启动并复现至少两条、人工复核受约束文件。不存在的异步、评分、技能、向量与密钥数据库字段需课程适配确认，不记为绿。真实扫描未命中，因此轮换条件未触发，未编造旧值401或历史重写。

以上事项完整列于 [剩余条件与范围](../../reports/security-gaps.md)。本地工作完成不等于这些外部验收已完成；课堂逐条提交由项目组自行处理。
