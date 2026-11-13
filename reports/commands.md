# 可重复命令盘点

最后更新：2026-11-13。以下时间来自真实运行记录；脚本无内部时间戳时明确使用证据文件生成时间，不伪造命令起止。全部为本地结果。

| 命令 | 最近时间（UTC） | 结果 | 证据 |
|---|---|---|---|
| `make check` | 2026-11-13T04:22:56.715693+00:00 | 退出0 | [输出](lesson10/final-check.txt) |
| `make check-security` | 2026-11-13T04:23:04.928516+00:00 | 退出0 | [输出](lesson10/final-security.txt) |
| `openspec validate 2026-11-11-lesson10-delivery-validation --strict` | 2026-11-13T04:23:06.125203+00:00 | 退出0 | [输出](lesson10/strict.txt) |
| `make image` | 证据生成 2026-11-13T04:23:00.419491+00:00 | 本地worktree标签、真实镜像ID | [原始](lesson10/build.json) |
| `.venv/bin/python -m scripts.verify_delivery` | 证据生成 2026-11-13T04:21:56.830933+00:00 | 临时目录201/404、重启保留、ready 200→503→200 | [原始](lesson10/runtime.json) |
| `.venv/bin/python -m scripts.verify_delivery --alerts` | 证据生成 2026-11-13T03:54:40.999631+00:00 | 本地真实触发与恢复；未通知外部负责人 | [原始](lesson10/alert-result.json) |
| `.venv/bin/python -m scripts.verify_workers` | 证据生成 2026-11-13T03:37:52.435979+00:00 | 三能力各10、双worker与重启 | [原始](lesson10/workers.json) |
| `.venv/bin/python -m scripts.verify_lease_crash` | 证据生成 2026-11-13T04:08:11.106895+00:00 | 35秒续约、异常25.06秒归零 | [原始](lesson10/lease-crash.json) |
| `.venv/bin/python -m scripts.verify_mobile` | 证据生成 2026-11-13T03:46:00.208866+00:00 | 自动化移动视口；非实机 | [原始](lesson10/mobile.json) |
| `.venv/bin/python -m scripts.scan_image --image <build.json中的image>` | 证据生成 2026-11-13T04:23:02.399125+00:00 | 最终保存层扫描范围内无命中 | [原始](lesson10/image-scan.json) |
| `.venv/bin/python -m scripts.bench` | 证据生成 2026-11-13T04:20:48.007051+00:00 | 90组合完成；原始样本同目录 | [原始](lesson10/bench/results.json) |
| `.venv/bin/python -m scripts.analyze_bench` | 证据生成 2026-11-13T04:21:51.749314+00:00 | 收益判据通过 | [原始](lesson10/bench/analysis.json) |
| `.venv/bin/python -m scripts.profile_search` | 证据生成 2026-11-13T04:00:25.978371+00:00 | 隔离FTS热点归因 | [原始](lesson10/search-profile.json) |
| `.venv/bin/python -m scripts.gate_red_green` | 实际恢复结束 2026-11-13T04:24:21.542377+00:00 | 坏断言非零→恢复0 | [原始](lesson10/gate/result.json) |
| `.venv/bin/python -m scripts.traceability` | 证据生成 2026-11-13T04:22:44.185618+00:00 | 34场景对应实际nodeid | [原始](lesson10/traceability.json) |

`make check`实际包含`make lint`、`make compile`、`make test`、`make layout`、`make secret-scan`、`make spec-check`；其整体时间/退出码见上。`make check-security`包含`make dependency-audit`同一审计脚本与32条安全用例。注入专项可用`.venv/bin/python -m pytest apitest/cases -q`重跑，已由本次双门禁实际执行。

开发入口`make setup`、`make run`及`docker compose up --build -d --wait`见README，配置后可重复；setup/run不是验收门禁，不填造本轮独立时间。`scripts.capture_dashboard`由观测脚本在真实实例中调用，不单独伪造截图。第九课`python scripts/verify_image.py`上次实际时间2026-11-11，证据保留在evidence/docker-verification.json，不冒充本次镜像扫描。

异步三判据从未执行：项目无该业务，不把同步201链路计为202任务通过。

所有Python命令需使用本仓库.venv/Python3.12；命令会更新相应证据，重跑前保留正式原始结果。

## 四技能落点差异

| 原课堂技能 | 当前落点 | 状态 |
|---|---|---|
| 解题引导不给最终答案 | 无解题技能 | 功能不存在，不能计绿 |
| 教师改分优先 | 无批改/改分 | 功能不存在，不能计绿 |
| 错题讲解不贴标准答案 | 无错题技能 | 功能不存在，不能计绿 |
| 知识库跨班为空 | test_sec02_both_search_paths、原检索隔离用例 | 基线已通过 |

方案1保留SQLite与同步上传/检索/问答，不引入空置MySQL/Qdrant或伪造队列指标。

## 本地提交后的最新门禁

实际提交`44a83af6439e8e1de9436be7f4197b921f2ca264`：make check于2026-11-13T04:37:34.787053+00:00退出0（85通过），make check-security于2026-11-13T04:37:54.816133+00:00退出0（32通过）。[命令、时间与源码](submission/committed-verification.json)。上表保留各专题实验时间。
