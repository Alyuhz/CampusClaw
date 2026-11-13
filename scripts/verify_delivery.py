from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime

from scripts.delivery_common import ROOT
from scripts.delivery_runtime import Runtime, runtime_flow


def fetch(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alerts", action="store_true")
    args = parser.parse_args()
    output = ROOT / "reports/lesson10"
    output.mkdir(exist_ok=True)
    runtime = Runtime()
    try:
        start = time.monotonic()
        runtime.start()
        result = runtime_flow(runtime)
        result["ready_seconds"] = time.monotonic() - start
        assert result["ready_seconds"] < 180
        (output / "runtime.json").write_text(json.dumps(result, indent=2))
        if not args.alerts:
            return
        result = runtime.compose("--profile", "telemetry", "up", "-d")
        runtime.wait(runtime.prom + "/-/ready")
        runtime.wait(runtime.grafana + "/api/health")
        teacher = runtime.client()
        student = runtime.client("student-a")
        for _ in range(10):
            assert teacher.upload("观测", "事务隔离观测")[0] == 201
            assert student.request("/api/v1/search?q=" + urllib.parse.quote("事务隔离"))[0] == 200
            status, csrf = student.request("/api/v1/auth/csrf")
            assert status == 200
            assert (
                student.request(
                    "/api/v1/ask",
                    "POST",
                    {"question": "事务隔离"},
                    {"X-CSRF-Token": csrf["data"]["csrf_token"]},
                )[0]
                == 200
            )
        assert student.request("/api/v1/search?q=")[0] == 400
        _, bad_csrf = student.request("/api/v1/auth/csrf")
        assert (
            student.request(
                "/api/v1/ask",
                "POST",
                {"question": ""},
                {"X-CSRF-Token": bad_csrf["data"]["csrf_token"]},
            )[0]
            == 400
        )
        began = time.time()
        received = None
        resolved = None
        threshold = None
        for tick in range(300):
            # Normal post-auth denial, no malformed data or business writes.
            assert student.upload("拒绝", "事务隔离")[0] == 403
            if tick % 3 == 0:
                assert (
                    student.request("/api/v1/search?q=" + urllib.parse.quote("事务隔离"))[0] == 200
                )
            if tick % 5 == 0:
                _, fresh = student.request("/api/v1/auth/csrf")
                assert (
                    student.request(
                        "/api/v1/ask",
                        "POST",
                        {"question": "事务隔离"},
                        {"X-CSRF-Token": fresh["data"]["csrf_token"]},
                    )[0]
                    == 200
                )
            if tick % 11 == 0:
                assert teacher.upload("实时曲线", "事务隔离观测")[0] == 201
            if tick == 60:
                from scripts.capture_dashboard import main as capture

                capture()
            time.sleep(1)
            if tick % 10 == 0:
                raw = runtime.compose(
                    "exec",
                    "-T",
                    "notify-sink",
                    "sh",
                    "-c",
                    "cat /evidence/notifications.jsonl 2>/dev/null || true",
                ).stdout
                records = [json.loads(line) for line in raw.splitlines() if line]
                alert_state = fetch(runtime.prom + "/api/v1/alerts")
                for alert in alert_state["data"]["alerts"]:
                    if alert["labels"].get("capability") == "materials-upload":
                        threshold = (
                            datetime.fromisoformat(
                                alert["activeAt"].replace("Z", "+00:00")
                            ).timestamp()
                            + 120
                        )
                firing = [row for row in records if row["status"] == "firing"]
                if firing:
                    received = firing[0]
                    (output / "alert-notifications.json").write_text(json.dumps(records, indent=2))
                    break
        assert received is not None, "No actual local webhook receipt in 5 minutes"
        assert threshold is not None and received["received_at"] - threshold <= 60
        assert received["received_at"] - began <= 300
        for query, name in [
            ("sum by (capability) (capability_requests_total)", "calls"),
            (
                'sum by (capability) (rate(capability_requests_total{status=~"4..|5.."}[2m])) / '
                "sum by (capability) (rate(capability_requests_total[2m]))",
                "errors",
            ),
            (
                "histogram_quantile(0.95,sum by (le,capability) "
                "(rate(capability_duration_seconds_bucket[2m])))",
                "p95",
            ),
            ("sum by (capability) (capability_inflight)", "inflight"),
        ]:
            data = fetch(runtime.prom + "/api/v1/query?" + urllib.parse.urlencode({"query": query}))
            assert data["status"] == "success" and data["data"]["result"], name
            (output / ("prom-" + name + ".json")).write_text(json.dumps(data, indent=2))
        # Wait for the two-minute window and evaluation/notification to resolve naturally.
        for tick in range(190):
            assert student.request("/api/v1/search?q=" + urllib.parse.quote("事务隔离"))[0] == 200
            time.sleep(1)
            if tick % 10 == 0:
                raw = runtime.compose(
                    "exec", "-T", "notify-sink", "cat", "/evidence/notifications.jsonl"
                ).stdout
                records = [json.loads(line) for line in raw.splitlines() if line]
                found = [row for row in records if row["status"] == "resolved"]
                if found:
                    resolved = found[-1]
                    break
        assert resolved is not None, "No actual recovery notification"
        (output / "alert-notifications.json").write_text(json.dumps(records, indent=2))
        (output / "alert-result.json").write_text(
            json.dumps(
                {
                    "started_epoch": began,
                    "first_received_epoch": received["received_at"],
                    "elapsed": received["received_at"] - began,
                    "recovery_received_epoch": resolved["received_at"],
                    "receiver": "local-test-webhook",
                    "condition_satisfied_epoch": threshold,
                    "delivery_delay_seconds": received["received_at"] - threshold,
                    "dashboard": runtime.grafana + "/d/campusclaw/capabilities",
                    "external_owner_notified": False,
                },
                indent=2,
            )
        )
        (output / "observability-runtime.json").write_text(
            json.dumps(
                {
                    "prometheus": runtime.prom,
                    "grafana": runtime.grafana,
                    "capabilities": ["materials-upload", "knowledge-search", "grounded-ask"],
                    "real_local_alert": True,
                    "runtime_cleaned_after": True,
                },
                indent=2,
            )
        )
        print("Local runtime, metrics and actual alert/recovery verified", flush=True)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
