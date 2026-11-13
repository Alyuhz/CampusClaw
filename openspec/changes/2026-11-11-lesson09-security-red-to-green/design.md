# Design

## Context

现有项目为 Flask/JWT/SQLite 与同步检索问答。文档阶段已完成；原功能基线 19 测试通过。新增四个真实红用例已复现：未装饰新接口可放行、底层写入无身份、CSRF 缺失可写、日志查询不存在。

## Goals / Non-Goals

**Goals:** 完成当前项目第九课安全修复、同场景复测、门禁与证据。
**Non-Goals:** 不造不存在的业务以模拟课表，不用替身结果冒充真实模型。

## Decisions

### 关键取舍

- auth.protect_api 对 /api/v1/ 默认认证，仅登录公开；从 JWT jti 查有效会话和当前用户。角色逐次判定，g.user 先于拒绝赋值，使 403 可审计。
- db.create_material 在 BEGIN IMMEDIATE 事务中检查服务端 session_id、教师角色、created_by 和 class_id；无身份 401、学生 403、跨班统一 404。低层直接调用也适用，不接受模型声称身份。详情按 ID 取单行再比归属，切片和 FTS/LIKE 保留 SQL 班级条件，不存在全表内存过滤路径。
- CSRF 使用 HttpOnly/SameSite=Strict 绑定 Cookie，生产默认 Secure；令牌只存 SHA256 摘要，绑定 jti 与 Cookie，10 分钟且原子消费。登录返回初始令牌，GET /api/v1/auth/csrf 刷新。前端每次写入单独取新令牌，不自动重放非幂等写入。
- migration 002 只新增 csrf_tokens、operation_logs。审计 JSON 七组：actor/timestamp/operation/object/result/skill_id/usage_and_duration；当前无技能协议，skill_id=null 且原因明确；未知用量 null，已知模型用量白名单筛选。对象截断 512 字符，事件上限 8192 字节，日志不记录请求正文/认证头/秘密。
- 上传成功与审计同事务；拒绝在回滚后独立留证。服务端独立 event_id 防重，不信任客户端 request_id 来去重。请求结束补耗时，审计失败返回 503，写入不能无审计成功。教师 GET /api/v1/audit-logs 仅本班，actor_id/UTC 起止/分页白名单，limit<=100、稳定排序。
- pip-audit 从官方 PyPI 安装并锁定；运行与开发锁均扫描，所有未登记已知漏洞阻断（严于仅高危）；异常/不可达阻断。例外要求精确包/版本/编号、理由、缓解、责任人与未过期日期；不匹配也拒绝。
- secret_scan 修复 Git diff +/- 前缀导致历史环境密钥漏检的问题。红绿在隔离临时仓库放合成风险，不把秘密提交到业务仓库。真实泄露才执行轮换与旧值拒绝验证；历史重写需全组协调。
- apitest/cases/test_injection.py 为常驻三件套；本机复用已安装 Chrome，CI 安装 Playwright 官方 Chromium。XSS 保存实际 outerHTML，CSRF 保存跨站 401 和无残留证据。
- SEC-08 前三步使用明确标识的恶意替身，允许输出被带偏并记录；第四步直接执行底层写入证明 403、无残留且留审计，不宣称不存在的模型工具协议已经实现。

## Risks / Trade-offs

- 一次性 CSRF 导致旧客户端失败 → 更新前端、示例和测试，跨账号共用测试 Cookie 必须刷新令牌。
- 审计数据库故障影响写入 → 事务回滚与 503 回归，不伪造日志。
- 没有真实模型凭证 → 替身实验证据独立，真实模型留待执行。
- 课表含本项目没有的异步/评分/向量 → 单列适配，原版全项验收不能宣称通过。

## Migration Plan

备份 SQLite，再部署新增迁移和客户端配套；保留旧业务数据。回滚应用时保留新增审计表，前后端一起回滚；恢复测试验证旧表与审计记录不丢失。外部调用不放事务内。完成后严格规约校验、make check 与 make check-security，归档另行执行。

## 本地交付版本

全部修改未提交、未推送，基线 e42b902 与 reports/evidence/source-manifest.json 定位实际代码。真实模型和组员人工复核仍待外部条件，不以文档框架代替实现验收。
