# CampusClaw 最终验收材料

本轮采用SQLite与同步知识库适配方案，保留三个真实能力：资料上传、知识检索、带出处问答。未新增批改技能、异步队列、MySQL或Qdrant，原版差异需课程确认。

代码与配置已推送到`codex/lesson09-security`分支，尚未合入main；[本地提交索引](reports/submission-commits.md)记录实际编号与逐提交检查。第九课证据保留；第十课本地双门禁通过：全量85条、安全专项32条；严格规约校验通过。机器验证与外部待办分别列明。

- 测试与场景：[命令盘点](reports/commands.md)、[追溯矩阵](reports/traceability.md)、[第十课最终核验](reports/lesson10/final-verification.json)。
- 门禁与运行：[红绿](reports/gate-red-green.md)、[干净目录运行](reports/lesson10/runtime.json)、[镜像层扫描](reports/lesson10/image-scan.json)。
- 观测：[真实告警](reports/lesson10/alert-result.json)、[面板](reports/lesson10/grafana-dashboard.png)、[多worker](reports/lesson10/workers.json)。
- 性能：[前后压测](reports/bench.md)：90组合完成且HTTP错误率0；固定热词并发1吞吐63.60→822.95req/s，P95 16.33→1.47ms，3次同方向。
- 使用：[移动视口](reports/lesson10/mobile.json)、[真实反馈](reports/feedback.md)。
- 高风险：[并发](reports/risk-concurrency.md)、[事务](reports/risk-transaction.md)、[授权](reports/risk-authz.md)。
- 评审：[脚本](reports/review-05.md)、[AI自审](reports/review-06.md)、[人工待执行](reports/review-07.md)。

真实手机、3名实际使用者、另一成员复核、远端主干保护/实际CI、外部负责人通知和课程适配尚待真实证据，不能计为全部验收通过。

远端检查：[实际推送与CI记录](reports/submission/push-verification.json)。分支上传成功；GitHub Actions因账号账单锁定未启动，尚不能判远端构建通过。
