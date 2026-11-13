from __future__ import annotations

import json
import platform
import statistics

from scripts.delivery_common import ROOT


def analyze(data):
    cases = data["cases"]
    comparisons = []
    saturation = []
    for concurrency in data["parameters"]["concurrency"]:
        before = sorted(
            (
                r
                for r in cases
                if r["variant"] == "before"
                and r["endpoint"] == "search"
                and r["concurrency"] == concurrency
            ),
            key=lambda r: r["repeat"],
        )
        after = sorted(
            (
                r
                for r in cases
                if r["variant"] == "after"
                and r["endpoint"] == "search"
                and r["concurrency"] == concurrency
            ),
            key=lambda r: r["repeat"],
        )
        if len(before) != 3 or len(after) != 3:
            continue
        old = statistics.median(r["throughput"] for r in before)
        new = statistics.median(r["throughput"] for r in after)
        oldp = statistics.median(r["p95_ms"] for r in before)
        newp = statistics.median(r["p95_ms"] for r in after)
        increase = (new / old - 1) * 100
        reduction = (1 - newp / oldp) * 100
        metric = "throughput" if increase >= reduction else "p95"
        repeats = sum(
            (a["throughput"] > b["throughput"])
            if metric == "throughput"
            else (a["p95_ms"] < b["p95_ms"])
            for b, a in zip(before, after, strict=True)
        )
        errors = any(a["error_rate"] > b["error_rate"] for b, a in zip(before, after, strict=True))
        comparisons.append(
            {
                "concurrency": concurrency,
                "before_throughput": old,
                "after_throughput": new,
                "before_p95_ms": oldp,
                "after_p95_ms": newp,
                "metric": metric,
                "improvement_percent": max(increase, reduction),
                "consistent_repeats": repeats,
                "error_rate_increased": errors,
            }
        )
    for variant in ["before", "after"]:
        for endpoint in ["submit", "query", "search"]:
            previous = None
            point = None
            reason = None
            for concurrency in data["parameters"]["concurrency"]:
                rows = [
                    r
                    for r in cases
                    if r["variant"] == variant
                    and r["endpoint"] == endpoint
                    and r["concurrency"] == concurrency
                ]
                if len(rows) != 3:
                    continue
                throughput = statistics.median(r["throughput"] for r in rows)
                p95 = statistics.median(r["p95_ms"] for r in rows)
                error = statistics.median(r["error_rate"] for r in rows)
                if error > 0.01 or p95 > 500 or (previous and throughput / previous < 1.1):
                    point = concurrency
                    reason = (
                        "error>1%"
                        if error > 0.01
                        else ("p95>500ms" if p95 > 500 else "adjacent throughput gain<10%")
                    )
                    break
                previous = throughput
            saturation.append(
                {
                    "variant": variant,
                    "endpoint": endpoint,
                    "concurrency": point,
                    "criterion": reason or "not observed through 32",
                }
            )
    verified = any(
        r["improvement_percent"] >= 10
        and r["consistent_repeats"] >= 2
        and not r["error_rate_increased"]
        for r in comparisons
    )
    return {
        "benefit_verified": verified,
        "search_comparisons": comparisons,
        "saturation": saturation,
    }


def main():
    folder = ROOT / "reports/lesson10/bench"
    data = json.loads((folder / "results.json").read_text())
    if len(data["cases"]) != 90:
        raise ValueError("Incomplete experiment: all 90 cases required")
    result = analyze(data)
    (folder / "analysis.json").write_text(json.dumps(result, indent=2))
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "shared_development_host": True,
        "workers": 2,
        "threads_per_worker": 4,
    }
    (folder / "environment.json").write_text(json.dumps(environment, indent=2))
    lines = [
        "# 第十课同条件压测",
        "",
        "状态：实际两轮、90个测量组合完成。只使用合成数据与随机测试凭证，无真实模型调用。",
        "",
        "固定相同热词的稳态命中负载，冷缓存只用于预热，不能外推为随机查询或冷启动收益。同一脚本、同参数、同数据快照，前后仅切检索缓存开关；双worker、每worker4线程、长连接。每点预热5秒、测20秒、重复3次，下面为3次中位数。",
        "",
        "吞吐为测量窗口内发起并收集完整响应的请求数/20秒，端到端延迟含尾部完成；上传包含CSRF获取成本，csrf_ms原始样本单列。HTTP非预期状态计错误，脚本不重放POST。",
        "",
        "| 版本 | 接口 | 并发 | 吞吐 req/s | P95 ms | HTTP错误率 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for variant in ["before", "after"]:
        for endpoint in ["submit", "query", "search"]:
            for concurrency in data["parameters"]["concurrency"]:
                rows = [
                    r
                    for r in data["cases"]
                    if (r["variant"], r["endpoint"], r["concurrency"])
                    == (variant, endpoint, concurrency)
                ]
                lines.append(
                    f"| {variant} | {endpoint} | {concurrency} | "
                    f"{statistics.median(r['throughput'] for r in rows):.2f} | "
                    f"{statistics.median(r['p95_ms'] for r in rows):.2f} | "
                    f"{statistics.median(r['error_rate'] for r in rows):.4%} |"
                )
    lines += [
        "",
        "## 改进判定",
        "",
        str(result["benefit_verified"]),
        "",
        "| 并发 | 比较指标 | 改善 | 同方向重复 | 错误率增加 |",
        "|---:|---|---:|---:|---|",
    ]
    for row in result["search_comparisons"]:
        lines.append(
            f"| {row['concurrency']} | {row['metric']} | "
            f"{row['improvement_percent']:.2f}% | {row['consistent_repeats']}/3 | "
            f"{row['error_rate_increased']} |"
        )
    lines += [
        "",
        "## 饱和判据与观察",
        "",
        "以首个错误率>1%、P95>500ms或相邻档吞吐提升<10%记录。未到阈值写未观测到，不外推。",
    ]
    for row in result["saturation"]:
        lines.append(
            f"- {row['variant']} / {row['endpoint']}: {row['concurrency']}, {row['criterion']}"
        )
    lines += [
        "",
        "## 归因与边界",
        "",
        "改进在同一班级/数据版本/查询/limit键下复用检索结果，减少重复FTS/rank/snippet计算；隔离100次cProfile中FTS累计约1.52秒，缓存命中检索路径约0.009秒，仅用于归因，不替代HTTP容量测量；计数、鉴权、审计与数据版本查询仍逐次执行。低成本查询与上传的剩余限制可能包括SQLite串行写、审计及协议成本，当前曲线不足以单独确认各自占比，不能用其吞吐称批改消费者吞吐。",
        "这是共享开发机测量，不是独占硬件容量认证；真实数据和外部模型延迟未纳入。原短连接试跑耗尽macOS临时端口，属客户端瓶颈，已隔离保留，不参与正式前后收益。",
        "",
        "[正式结果与来源](lesson10/bench/results.json)、[隔离profile](lesson10/search-profile.json)、[实测源码快照](lesson10/measured-source.zip)、[分析](lesson10/bench/analysis.json)、[环境](lesson10/bench/environment.json)、[脚本/参数/数据摘要](lesson10/bench/manifest.json)。",
        "本地未提交版本用基线与工作区摘要定位，没有伪造改进提交号。实测业务包、主脚本与锁文件逐文件哈希匹配归档；HTTP辅助模块由同一实验进程一次导入并用于前后两轮，其原始摘要在manifest，当前辅助文件已更新，不冒充原始文件快照。随后仅补就绪依赖表检查、指标无效凭据处理与非零seed参数的实际作用，默认seed=0的业务负载保持不变。复跑原主脚本可从快照提取；最终门禁另验最终源码。",
    ]
    (ROOT / "reports/bench.md").write_text("\n".join(lines) + "\n")
    if not result["benefit_verified"]:
        raise SystemExit("Measured benefit not sufficient; investigate and rerun")
    print("Same-condition improvement verified.")


if __name__ == "__main__":
    main()
