# 变更验证：lesson-07-completion

## 原因

首版代码完成量领先于第 7 课骨架，但配置默认值、非 JSON 框架日志、前端状态、幂等声明和
OpenSpec 严格校验没有形成完整证据链。

## 影响

- 应用配置全部改为外部必填；
- 请求访问日志改为唯一来源的 JSON；
- 修正 Dockerfile 中无效的 Gunicorn `--factory` 参数；
- 补齐界面状态、幂等契约、失败场景与工程规范判据；
- 增加 OpenSpec 原生严格校验和第 7 课验证目录；
- `main` 增加 PR、审批、状态检查和禁止强推保护。

## 验证

执行 `make check`，结果为 37 个测试通过，Ruff、格式、编译、分层、密钥扫描和 OpenSpec
严格校验全部通过。详细输出和外部待办见 `docs/lesson-07/verification.md`。

## 未关闭项

Docker 实机、真实 GLM、组内交叉评审和回滚演练尚未完成；因此本变更暂不归档、不打标签。
