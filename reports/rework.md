# 第九课返工与复盘

## 实际发现：镜像能构建但启动即退出

在实际容器验收中，原 Dockerfile 使用 Gunicorn 不支持的 `--factory` 参数，进程立即退出。此前只有本机 Flask 用例，未发现部署入口不可用。[失败日志](evidence/docker-runtime-before.txt) 原文为 `gunicorn: error: unrecognized arguments: --factory`。

改法：入口改为 Gunicorn 支持的 `campusclaw:create_app()`；启动两 worker 的同时检查首次迁移竞争，将版本读取和 DDL 放进 BEGIN IMMEDIATE 事务，并补并行初始化回归。

实际验证：镜像健康为 ok、UID 10001、两 worker 能启动、备份恢复与重复/并发迁移通过；[运行日志](evidence/docker-runtime.txt)、[镜像摘要与扫描](evidence/docker-verification.json)。

计时：有记录的修复开始到首次健康验证后记录点为 59.95 秒，包含构建与其他检查交错等待，是壁钟间隔，不等同纯编码时长。最初定位起点未计时，定位耗时记未测量，不编造分钟数。

当时怎么错：将镜像构建通过误当成服务可运行，入口参数没有真实启动验证。一条可执行改法：发布前运行 `python scripts/verify_image.py`，要求 health 成功、非 root 并自动清理临时容器；失败即阻断。

## 修复中的功能回归：CSRF 与测试账号共用 Cookie

首次加入一次性 CSRF 后，原 `test_search_and_ask_only_use_current_class` 的 A 学生问答从 200 变 403，因为同一测试客户端又登录 B，绑定 Cookie 已更新而 A 仍用旧令牌。定位后在切回 A 的请求前按真实客户端流程重新获取 A 会话绑定的一次性令牌，没有关闭 CSRF 或降低断言。该失败曾实测为 1 failed/22 passed，随后原功能与新增用例全部通过。

可执行改法：不同账号用独立客户端；确需共享 Cookie 的用例，每次写入前从 auth/csrf 取令牌。定位/修复没有独立秒表记录，耗时未测量。
