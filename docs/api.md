# CampusClaw API

所有 `/api/v1/` JSON 响应共享以下结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

除登录和健康检查外，请求需携带 `Authorization: Bearer <token>`。每次响应都带
`X-Request-ID`；客户端可提供 8–64 位字母、数字或连字符组成的标识，否则服务端生成。

## 健康检查

`GET /health`，无需认证。

成功示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "time": "2026-10-28T02:00:00+00:00",
    "dependencies": {"database": "ok"}
  }
}
```

## 登录

`POST /api/v1/auth/login`

```json
{"username": "student-a", "password": "<本机配置中的学生口令>"}
```

成功返回 Bearer token、用户名、角色和班级。错误账号与错误口令均返回相同的
`401 / code=1101`。

## 当前用户与退出

- `GET /api/v1/me`：返回当前用户、角色和服务端用户记录中的班级。
- `POST /api/v1/auth/logout`：吊销当前令牌，后续使用该令牌返回 401。

## 资料

`GET /api/v1/materials` 返回当前用户本班资料，不返回其他班数据。

教师上传：`POST /api/v1/materials`，`multipart/form-data`：

- `file`：UTF-8 的 `.md` 或 `.txt`，默认上限 1 MiB；
- `title`：可选，最长 120 字符。

详情：`GET /api/v1/materials/{id}`。跨班资料与不存在资料均返回相同的
`404 / code=1304` 响应体。

## 检索

`GET /api/v1/search?q=<关键词>&limit=<1..20>`

查询词长度 1–200。返回命中切片、资料标题、起止行号、摘要和分数。班级只从当前认证
用户记录读取；query 中的 `class_id` 会被忽略。

## 问答

`POST /api/v1/ask`

```json
{"question": "事务隔离级别是什么？"}
```

问题长度 1–300。最多返回五条真实命中作为 citations：

- 配置 `GLM_API_KEY` 时调用 GLM，并使用版本化系统提示词；
- 未配置 Key 时返回确定性抽取式回答，`degraded=true`；
- 无命中时固定返回“资料中未找到相关内容”，`citations=[]`；
- 模型不可达时返回 `503 / code=1500`。

## 错误码

| code | HTTP | 含义 |
|---|---:|---|
| 0 | 2xx | 成功 |
| 1100 | 401 | 未登录或令牌无效 |
| 1101 | 400/401 | 参数错误或登录失败 |
| 1102 | 415 | 文件类型或编码不支持 |
| 1103 | 413 | 文件超过大小上限 |
| 1105 | 405 | 请求方法不允许 |
| 1204 | 403/404 | 无权操作；资源型越权使用统一 404 |
| 1304 | 404 | 资源不存在 |
| 1500 | 500/503 | 系统错误或依赖不可达 |


## 第九课安全接口更新

受保护 /api/v1/ 默认在入口验证 Bearer，新增接口也不能漏检；公开登录、页面静态资源与 health 不变。状态变更请求除登录外增加一次性 CSRF 要求，这是客户端兼容性变更。

登录成功返回 token、user、csrf_token，并设置 csrf_binding Cookie（HttpOnly、SameSite=Strict；默认 Secure）。本机 HTTP 开发须在 .env 明确 COOKIE_SECURE=false；生产 HTTPS 使用 true。

`GET /api/v1/auth/csrf`：携带有效 Bearer 和浏览器绑定 Cookie，返回新 csrf_token。令牌存储仅摘要，绑定会话与 Cookie，10 分钟有效且只能用一次。写请求添加 X-CSRF-Token；即使业务参数失败，已消费的令牌也不可重放，重试前重新获取。Cookie 不是登录凭据，Bearer 仍必需。无身份 401；有效身份缺失/过期/重放/错绑定 CSRF 为 403/code=1204；学生教师写接口同样 403。

命令行客户端使用 curl 的 -c/-b Cookie jar 保留绑定，再用当前 csrf_token 写入；不要将认证值保存到报告。前端已按每次写前取新令牌适配，不自动重放非幂等上传。上传是非幂等创建；退出重复使用已吊销会话为 401，不能重复提交兜底。

`GET /api/v1/audit-logs`：仅教师可查本班。可选 actor_id（正整数）、start/end（带时区 ISO8601，归一 UTC）、limit（1..100，默认50）、offset（>=0，默认0）。未知筛选、非法数值或时间窗返回 400；学生返回 403；跨班记录不返回。排序 created_at DESC,id DESC。成功返回 data.items 的七列 JSON 事件，包含 event_id。

事件字段：actor、timestamp、operation、object、result、skill_id、usage_and_duration；无技能协议时 skill_id=null 且 skill_reason=not_applicable。已知 token 用量按白名单记录，未知为 null。对象最长512字符、事件最多8192字节，不存秘密或正文。写业务与成功审计同事务；审计存储不可用返回 503/code=1500 并回滚上传。

安全验证入口：make check（含 apitest/cases/ 的可执行三件套）、make check-security（秘密历史与两份锁文件依赖审计）。

## 第十课交付与验证

- `GET /ready`：免认证，只读检查必要数据表和迁移。就绪200，数据库不可达/必要结构缺失503，不调用模型、不创建业务数据。仅提供状态，不返回数据库细节。
- `GET /internal/metrics`：仅 `TELEMETRY_ENABLED=true` 时启用，使用独立 `Authorization: Bearer <METRICS_TOKEN>`；业务JWT不适用，无效凭据401。关闭时404。计数及耗时直方图持久化，固定capability/status标签，不带身份、班级、问题、正文；存储故障不能伪装为零值。此接口供内部抓取，勿向公网开放。
- `capability_requests_total`、`capability_duration_seconds`沿用审计操作结果；capability为materials-upload、knowledge-search、grounded-ask。`capability_inflight`为带30秒过期与续约的执行中lease，不是异步队列。
- 当前上传成功201、检索/问答200；不提供202任务与轮询接口。手机视口复用相同认证、CSRF与同源API。
