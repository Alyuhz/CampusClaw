from __future__ import annotations

import concurrent.futures
import json
import re
import urllib.request

from scripts.delivery_common import ROOT
from scripts.delivery_runtime import Runtime


def totals(runtime):
    request = urllib.request.Request(
        runtime.url + "/internal/metrics",
        headers={"Authorization": "Bearer " + runtime.config["METRICS_TOKEN"]},
    )
    with urllib.request.urlopen(request) as response:
        text = response.read().decode()
    result = {}
    for cap, status, count in re.findall(
        r'capability_requests_total\{capability="([^"]+)",status="(\d+)"\} ([\d.]+)', text
    ):
        if status in {"200", "201"}:
            result[cap] = result.get(cap, 0) + int(float(count))
    return result


def main():
    runtime = Runtime()
    try:
        runtime.start()
        baseline = totals(runtime)

        def exercise(index):
            teacher = runtime.client()
            assert teacher.upload("worker", "事务隔离两进程")[0] == 201
            assert teacher.request("/api/v1/search?q=%E4%BA%8B%E5%8A%A1")[0] == 200
            _, csrf = teacher.request("/api/v1/auth/csrf")
            assert (
                teacher.request(
                    "/api/v1/ask",
                    "POST",
                    {"question": "事务"},
                    {"X-CSRF-Token": csrf["data"]["csrf_token"]},
                )[0]
                == 200
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(exercise, range(10)))
        after = totals(runtime)
        assert all(
            after.get(cap, 0) - baseline.get(cap, 0) == 10
            for cap in ["materials-upload", "knowledge-search", "grounded-ask"]
        )
        runtime.compose("restart", "app")
        runtime.wait(runtime.url + "/ready")
        restarted = totals(runtime)
        assert restarted == after
        (ROOT / "reports/lesson10/workers.json").write_text(
            json.dumps(
                {
                    "configured_workers": 2,
                    "parallel_clients": 4,
                    "baseline": baseline,
                    "after": after,
                    "after_restart": restarted,
                    "each_capability_increment": 10,
                },
                indent=2,
            )
        )
        print("Two-worker HTTP counters exact and persistent.")
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
