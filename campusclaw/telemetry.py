from __future__ import annotations

import hmac
import json
import threading

from flask import Flask, Response, request

from . import db
from .http import api_response


class Leases:
    def __init__(self, app: Flask):
        self.app = app
        self.lock = threading.Lock()
        self.events: set[str] = set()
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def add(self, event: str, capability: str) -> None:
        db.begin_lease(event, capability)
        with self.lock:
            self.events.add(event)
            if self.thread is None and not self.app.testing:
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

    def discard(self, event: str) -> None:
        with self.lock:
            self.events.discard(event)

    def _run(self) -> None:
        while not self.stop.wait(5):
            with self.lock:
                events = list(self.events)
            if events:
                try:
                    with self.app.app_context():
                        db.renew_leases(events)
                except Exception:
                    self.app.logger.error("metric lease renewal unavailable")

    def close(self) -> None:
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=6)


def register_metrics(app: Flask) -> None:
    app.extensions["leases"] = Leases(app)

    @app.get("/internal/metrics")
    def metrics() -> Response | tuple:
        expected = app.config["METRICS_TOKEN"]
        supplied = request.headers.get("Authorization", "")
        if not app.config["TELEMETRY_ENABLED"]:
            return api_response(None, code=1304, message="资源不存在", status=404)
        if not hmac.compare_digest(
            supplied.encode("utf-8"), ("Bearer " + expected).encode("utf-8")
        ):
            return api_response(None, code=1100, message="未登录", status=401)
        try:
            totals, active = db.metric_snapshot()
        except Exception:
            return api_response(None, code=1500, message="指标存储不可用", status=503)
        lines = [
            "# TYPE capability_requests_total counter",
            "# TYPE capability_duration_seconds histogram",
            "# TYPE capability_inflight gauge",
        ]
        for row in totals:
            labels = f'capability="{row["capability"]}",status="{row["status"]}"'
            lines.append(f"capability_requests_total{{{labels}}} {row['n']}")
            lines.append(f"capability_duration_seconds_count{{{labels}}} {row['n']}")
            lines.append(f"capability_duration_seconds_sum{{{labels}}} {row['sum_seconds']}")
            for bound, count in zip(
                (*db.METRIC_BOUNDS, "+Inf"), json.loads(row["buckets"]), strict=True
            ):
                lines.append(f'capability_duration_seconds_bucket{{{labels},le="{bound}"}} {count}')
        for capability in db.CAPABILITIES.values():
            lines.append(
                f'capability_inflight{{capability="{capability}"}} {active.get(capability, 0)}'
            )
        return Response("\n".join(lines) + "\n", mimetype="text/plain")
