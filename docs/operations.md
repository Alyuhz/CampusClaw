# 运行与发布

## 运行

1. 从 `.env.example` 复制 `.env` 并填写全部空值。
2. `make setup`
3. `make run`
4. `curl --fail http://127.0.0.1:5000/health`

容器环境执行 `docker compose up --build -d`。SQLite 文件位于容器卷
`campusclaw-data:/app/instance`。

`make run` 使用 Gunicorn 加载 `.env`；`WEB_PORT` 为空或缺失时立即失败，不会猜测端口。

开发、测试和生产使用同一镜像，仅通过 `.env` 替换版本、数据库路径、密钥、模型 Key 和
公开端口。配置没有代码默认值；升级前必须补齐示例中的全部键。

## 健康与日志

`/health` 返回版本、UTC 时间与数据库状态。HTTP 非 2xx 表示不可接流量。

stdout 日志为单行 JSON，字段包括时间、级别、模块、请求标识、方法、路径、状态和耗时。
不得记录密钥、口令、资料正文或问题原文。

应用请求日志是唯一访问日志；Werkzeug 默认访问日志已关闭，Gunicorn access log 也关闭，
error log 使用 JSON formatter。Gunicorn 收到 SIGTERM 后最多等待 30 秒处理在途请求。

## 备份

发布前备份 `instance/campusclaw.sqlite3`。备份与恢复目标：

- RPO：24 小时；
- RTO：1 小时；
- 每学期至少执行一次恢复演练并记录耗时。

## 发布顺序

1. `make check`
2. 构建镜像并按提交号打标签；
3. 备份数据库；
4. 执行向后兼容迁移；
5. 启动新版本；
6. 等待 `/health` 成功；
7. 记录版本、变更、验证结论与耗时。

初始结构位于 `campusclaw/migrations/001_initial.sql`。后续结构变化必须新增不可变迁移文件，
禁止直接修改已执行迁移；每次迁移文件头应写清回滚动作。

数据留存与备份：资料和切片保留到班级明确删除或课程结束；问题原文不持久化；认证会话在
过期后保留 30 天；备份最多保留 7 天。

## 回滚

回滚目标只允许是上一版本标签。先在测试环境恢复对应镜像与兼容数据库，再切换流量。
未演练过的回滚视为不可用。记录镜像标签、数据库备份、执行命令与恢复耗时。
