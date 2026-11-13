from __future__ import annotations

import http.client

import pytest

from scripts.bench import summary
from scripts.delivery_common import Client


def test_transport_does_not_replay_uncertain_write(monkeypatch):
    calls = []

    class Broken:
        def request(self, *args, **kwargs):
            calls.append(args)

        def getresponse(self):
            raise http.client.RemoteDisconnected()

        def close(self):
            pass

    monkeypatch.setattr(http.client, "HTTPConnection", lambda *a, **k: Broken())
    client = Client("http://127.0.0.1:1")
    with pytest.raises(http.client.RemoteDisconnected):
        client.request("/api/v1/materials", "POST", {})
    assert len(calls) == 1


def test_transport_reconnects_safe_read_once(monkeypatch):
    calls = []

    class Broken:
        def request(self, *args, **kwargs):
            calls.append(args)

        def getresponse(self):
            raise http.client.RemoteDisconnected()

        def close(self):
            pass

    monkeypatch.setattr(http.client, "HTTPConnection", lambda *a, **k: Broken())
    with pytest.raises(http.client.RemoteDisconnected):
        Client("http://127.0.0.1:1").request("/ready")
    assert len(calls) == 2


def test_percentile_throughput_and_errors():
    rows = [{"ms": i, "ok": i != 20} for i in range(1, 21)]
    result = summary(rows, 10)
    assert result == {"samples": 20, "throughput": 2, "p95_ms": 19, "error_rate": 0.05}


def test_build_refuses_false_clean_revision(monkeypatch):
    from scripts import build_image

    monkeypatch.setattr(
        build_image, "source_snapshot", lambda: {"base_commit": "a" * 40, "sha256": "b" * 64}
    )
    monkeypatch.setenv("SOURCE_REVISION", "a" * 40)
    monkeypatch.setattr(build_image.subprocess, "check_output", lambda *a, **k: "dirty.py\n")
    with pytest.raises(ValueError, match="Dirty"):
        build_image.main()


def test_benchmark_analysis_does_not_hide_more_errors():
    from scripts.analyze_bench import analyze

    data = {"parameters": {"concurrency": [1]}, "cases": []}
    for variant in ["before", "after"]:
        for repeat in range(3):
            data["cases"].append(
                {
                    "variant": variant,
                    "repeat": repeat,
                    "endpoint": "search",
                    "concurrency": 1,
                    "throughput": 10 if variant == "before" else 20,
                    "p95_ms": 100 if variant == "before" else 50,
                    "error_rate": 0 if variant == "before" else 0.2,
                }
            )
    assert not analyze(data)["benefit_verified"]
    for row in data["cases"]:
        row["error_rate"] = 0
    assert analyze(data)["benefit_verified"]


def test_benchmark_rejects_error_increase_in_one_repeat():
    from scripts.analyze_bench import analyze

    cases = [
        {
            "variant": variant,
            "repeat": repeat,
            "endpoint": "search",
            "concurrency": 1,
            "throughput": 10 if variant == "before" else 20,
            "p95_ms": 100,
            "error_rate": 0.2 if variant == "after" and repeat == 0 else 0,
        }
        for variant in ["before", "after"]
        for repeat in range(3)
    ]
    assert not analyze({"parameters": {"concurrency": [1]}, "cases": cases})["benefit_verified"]
