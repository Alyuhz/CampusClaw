# 需求规约：class-material-search

### 场景：合法账号登录

- **前置条件**：系统中存在属于 class-a 的 student-a，种子口令已配置。
- **操作**：提交正确账号口令到 `POST /api/v1/auth/login`。
- **可观测结果**：返回 200、code=0，响应含 Bearer token；`/api/v1/me` 返回 student-a
  与 class-a。

### 场景：登录失败不泄露账号是否存在

- **前置条件**：student-a 已存在。
- **操作**：分别用不存在账号和 student-a 配错误口令登录。
- **可观测结果**：两次均返回 401、code=1101，响应体完全一致。

### 场景：教师上传 Markdown 资料

- **前置条件**：teacher-a 已登录并属于 class-a。
- **操作**：以 multipart 上传 UTF-8 Markdown 文件。
- **可观测结果**：返回 201、code=0；资料与至少一个切片写入 class-a，FTS 可检索。

### 场景：学生调用教师上传接口

- **前置条件**：student-a 已登录。
- **操作**：调用 `POST /api/v1/materials` 上传文件。
- **可观测结果**：返回 403、code=1204，资料数量不变化。

### 场景：读取跨班或不存在的资料

- **前置条件**：class-a 存在资料 M；teacher-b 属于 class-b。
- **操作**：teacher-b 分别请求 `GET /api/v1/materials/M` 和不存在的资料 ID。
- **可观测结果**：两者均返回 404、code=1304，且响应体逐字节一致。

### 场景：仅检索本班资料

- **前置条件**：class-a 存在包含“事务隔离”的资料；student-b 属于 class-b。
- **操作**：student-a 与 student-b 分别请求 `GET /api/v1/search?q=事务隔离`。
- **可观测结果**：student-a 至少得到一条命中；student-b 的 items 为空。

### 场景：问题带真实出处回答

- **前置条件**：class-a 存在与问题匹配的资料且未配置 GLM Key。
- **操作**：student-a 调用 `POST /api/v1/ask`。
- **可观测结果**：返回 200、code=0；citations 均来自 class-a，编号可指向实际切片，
  `degraded=true`。

### 场景：无依据问题不编造出处

- **前置条件**：本班资料与问题无关。
- **操作**：学生调用 `POST /api/v1/ask`。
- **可观测结果**：返回 200、code=0；answer 为“资料中未找到相关内容”，citations 为空。

### 场景：客户端伪造班级参数

- **前置条件**：class-a 存在资料；student-b 已登录。
- **操作**：请求 `/api/v1/search?q=测试&class_id=class-a`。
- **可观测结果**：服务端忽略 query 中的班级，仍返回 class-b 的检索结果。

### 场景：健康检查免认证

- **前置条件**：应用与数据库已启动。
- **操作**：不携带令牌请求 `GET /health`。
- **可观测结果**：返回 200、code=0；data 含 status、version、time 和 database 状态。
