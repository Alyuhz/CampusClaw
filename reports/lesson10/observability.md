# 真实观测与告警

手段：`python -m scripts.verify_delivery --alerts`，独立临时Compose的telemetry profile，产生上传/检索/问答三种流量及持续403；实际启动Prometheus、Grafana、Alertmanager与本地接收器。

面板分组：调用量分能力曲线；每能力错误率由计数相除；P95与执行中请求并排。capability只含materials-upload、knowledge-search、grounded-ask，不含个人/班级/正文。执行中请求使用跨worker lease，不代表异步队列。

证据：[实际面板](grafana-dashboard.png)、[运行信息](observability-runtime.json)、[调用量](prom-calls.json)、[错误率](prom-errors.json)、[P95](prom-p95.json)、[执行中](prom-inflight.json)。

告警判据：2分钟窗口至少20请求，错误率>1%持续2分钟→本地接收器→附此次实际实例面板链接；恢复同样通知。满足持续条件后60秒内、实验5分钟内送达为绿。

实际从实验开始到首次收件156.3386526107788秒；精确阈值时刻、收件、恢复与面板链接见 [真实记录](alert-result.json)、[脱敏回执](alert-notifications.json)。本地收件与恢复已验证，未配置外部负责人渠道，不能代替真实负责人通知。临时实例测试后已清理，历史链接供来源核查，不承诺仍在线。

[worker计数与重启](workers.json)、[35秒续约及异常过期](lease-crash.json)、[Grafana缺口令拒启](grafana-password-guard.json)。
