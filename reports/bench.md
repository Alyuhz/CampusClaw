# 第十课同条件压测

状态：实际两轮、90个测量组合完成。只使用合成数据与随机测试凭证，无真实模型调用。

固定相同热词的稳态命中负载，冷缓存只用于预热，不能外推为随机查询或冷启动收益。同一脚本、同参数、同数据快照，前后仅切检索缓存开关；双worker、每worker4线程、长连接。每点预热5秒、测20秒、重复3次，下面为3次中位数。

吞吐为测量窗口内发起并收集完整响应的请求数/20秒，端到端延迟含尾部完成；上传包含CSRF获取成本，csrf_ms原始样本单列。HTTP非预期状态计错误，脚本不重放POST。

| 版本 | 接口 | 并发 | 吞吐 req/s | P95 ms | HTTP错误率 |
|---|---|---:|---:|---:|---:|
| before | submit | 1 | 327.10 | 3.65 | 0.0000% |
| before | submit | 4 | 316.95 | 43.81 | 0.0000% |
| before | submit | 8 | 312.90 | 57.14 | 0.0000% |
| before | submit | 16 | 315.50 | 82.69 | 0.0000% |
| before | submit | 32 | 310.40 | 135.46 | 0.0000% |
| before | query | 1 | 1042.70 | 1.17 | 0.0000% |
| before | query | 4 | 916.25 | 12.31 | 0.0000% |
| before | query | 8 | 912.40 | 16.88 | 0.0000% |
| before | query | 16 | 928.90 | 25.41 | 0.0000% |
| before | query | 32 | 914.90 | 45.31 | 0.0000% |
| before | search | 1 | 63.60 | 16.33 | 0.0000% |
| before | search | 4 | 44.25 | 288.69 | 0.0000% |
| before | search | 8 | 44.25 | 335.01 | 0.0000% |
| before | search | 16 | 44.35 | 532.26 | 0.0000% |
| before | search | 32 | 44.45 | 907.32 | 0.0000% |
| after | submit | 1 | 190.85 | 8.02 | 0.0000% |
| after | submit | 4 | 173.15 | 75.30 | 0.0000% |
| after | submit | 8 | 181.45 | 152.44 | 0.0000% |
| after | submit | 16 | 187.35 | 222.20 | 0.0000% |
| after | submit | 32 | 173.50 | 652.74 | 0.0000% |
| after | query | 1 | 862.10 | 1.26 | 0.0000% |
| after | query | 4 | 822.45 | 12.33 | 0.0000% |
| after | query | 8 | 752.20 | 28.01 | 0.0000% |
| after | query | 16 | 790.10 | 39.47 | 0.0000% |
| after | query | 32 | 794.85 | 58.28 | 0.0000% |
| after | search | 1 | 822.95 | 1.47 | 0.0000% |
| after | search | 4 | 653.35 | 15.86 | 0.0000% |
| after | search | 8 | 556.90 | 45.80 | 0.0000% |
| after | search | 16 | 532.80 | 65.40 | 0.0000% |
| after | search | 32 | 494.45 | 148.21 | 0.0000% |

## 改进判定

True

| 并发 | 比较指标 | 改善 | 同方向重复 | 错误率增加 |
|---:|---|---:|---:|---|
| 1 | throughput | 1193.95% | 3/3 | False |
| 4 | throughput | 1376.50% | 3/3 | False |
| 8 | throughput | 1158.53% | 3/3 | False |
| 16 | throughput | 1101.35% | 3/3 | False |
| 32 | throughput | 1012.37% | 3/3 | False |

## 饱和判据与观察

以首个错误率>1%、P95>500ms或相邻档吞吐提升<10%记录。未到阈值写未观测到，不外推。
- before / submit: 4, adjacent throughput gain<10%
- before / query: 4, adjacent throughput gain<10%
- before / search: 4, adjacent throughput gain<10%
- after / submit: 4, adjacent throughput gain<10%
- after / query: 4, adjacent throughput gain<10%
- after / search: 4, adjacent throughput gain<10%

## 归因与边界

改进在同一班级/数据版本/查询/limit键下复用检索结果，减少重复FTS/rank/snippet计算；隔离100次cProfile中FTS累计约1.52秒，缓存命中检索路径约0.009秒，仅用于归因，不替代HTTP容量测量；计数、鉴权、审计与数据版本查询仍逐次执行。低成本查询与上传的剩余限制可能包括SQLite串行写、审计及协议成本，当前曲线不足以单独确认各自占比，不能用其吞吐称批改消费者吞吐。
这是共享开发机测量，不是独占硬件容量认证；真实数据和外部模型延迟未纳入。原短连接试跑耗尽macOS临时端口，属客户端瓶颈，已隔离保留，不参与正式前后收益。

[正式结果与来源](lesson10/bench/results.json)、[隔离profile](lesson10/search-profile.json)、[实测源码快照](lesson10/measured-source.zip)、[分析](lesson10/bench/analysis.json)、[环境](lesson10/bench/environment.json)、[脚本/参数/数据摘要](lesson10/bench/manifest.json)。
本地未提交版本用基线与工作区摘要定位，没有伪造改进提交号。实测业务包、主脚本与锁文件逐文件哈希匹配归档；HTTP辅助模块由同一实验进程一次导入并用于前后两轮，其原始摘要在manifest，当前辅助文件已更新，不冒充原始文件快照。随后仅补就绪依赖表检查、指标无效凭据处理与非零seed参数的实际作用，默认seed=0的业务负载保持不变。复跑原主脚本可从快照提取；最终门禁另验最终源码。

## 本地提交补记

2026-11-13：缓存改进的实际实现提交为`44a83af6439e8e1de9436be7f4197b921f2ca264`。原实验的工作区摘要与先红后绿输出保持原样；没有将隔离副本的故意坏断言编造为项目提交。SEC分项编号见[提交索引](submission-commits.md)。提交后的双门禁再次通过，见[真实核验](submission/committed-verification.json)。
