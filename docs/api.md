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
