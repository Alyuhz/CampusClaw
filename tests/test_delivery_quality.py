from __future__ import annotations

import json
import re

from scripts.delivery_common import ROOT

EVIDENCE = ROOT / "reports/lesson10"


def load(name):
    return json.loads((EVIDENCE / name).read_text())


def test_traceability_nodes_are_collectable():
    from scripts.traceability import build

    entries = build()
    assert len(entries) == 34 and all(row["nodeids"] for row in entries)


def test_actual_bad_assertion_red_green():
    data = load("gate/result.json")
    assert [run["exit_code"] == 0 for run in data["runs"]] == [False, True]
    assert all(run["command"] == "make check" for run in data["runs"])
    assert "299" in (EVIDENCE / "gate/mutation.diff").read_text()
    assert data["main_worktree_untouched"] and not data["project_commits_created"]


def test_ci_gates_precede_build():
    workflow = (ROOT / ".github/workflows/check.yml").read_text()
    assert (
        workflow.index("run: make check PYTHON=python")
        < workflow.index("run: make check-security PYTHON=python")
        < workflow.index("run: make image PYTHON=python")
    )
    assert "continue-on-error: true" not in workflow
    assert "fetch-depth: 0" in workflow


def test_actual_clean_runtime():
    data = load("runtime.json")
    assert data["ready_seconds"] < 180
    assert data["upload"] == 201 and data["cross_class"] == 404 and data["identical_404"]
    assert (
        data["restart_data_retained"] and data["uid"] != "0" and data["application_py_files"] == 0
    )
    assert len(data["build_info"]["application_sha256"]) == 64


def test_actual_workers_and_restart():
    data = load("workers.json")
    assert data["configured_workers"] == 2 and data["after_restart"] == data["after"]
    for cap in ["materials-upload", "knowledge-search", "grounded-ask"]:
        assert data["after"].get(cap, 0) - data["baseline"].get(cap, 0) == 10


def test_actual_dashboard_queries():
    panel = load("dashboard-provisioned.json")
    assert len(panel["panels"]) == 4
    for name in ["calls", "errors", "p95", "inflight"]:
        rows = load("prom-" + name + ".json")["data"]["result"]
        assert {row["metric"]["capability"] for row in rows} == {
            "materials-upload",
            "knowledge-search",
            "grounded-ask",
        }
    assert (EVIDENCE / "grafana-dashboard.png").stat().st_size > 10000


def test_actual_alert_delivery_and_recovery():
    result = load("alert-result.json")
    records = load("alert-notifications.json")
    assert result["elapsed"] <= 300 and not result["external_owner_notified"]
    assert 0 <= result["delivery_delay_seconds"] <= 60
    assert {row["status"] for row in records} >= {"firing", "resolved"}
    assert result["recovery_received_epoch"] > result["first_received_epoch"]


def test_benchmark_matching_protocol():
    data = load("bench/results.json")
    p = data["parameters"]
    assert p["duration"] == 20 and p["warmup"] == 5 and p["repeats"] == 3
    assert p["concurrency"] == [1, 4, 8, 16, 32] and p["workers"] == 2
    assert len(data["cases"]) == 90
    assert len(data["script_sha256"]) == 64 and len(data["data"]["sha256"]) == 64
    assert all(row["samples"] > 0 and row["p95_ms"] is not None for row in data["cases"])


def test_benchmark_actual_benefit():
    result = load("bench/analysis.json")
    assert result["benefit_verified"]
    assert any(
        row["improvement_percent"] >= 10
        and row["consistent_repeats"] >= 2
        and not row["error_rate_increased"]
        for row in result["search_comparisons"]
    )


def test_actual_mobile_viewport():
    data = load("mobile.json")
    assert not data["real_phone"] and data["kind"] == "automated-mobile-viewport"
    assert [data[k] for k in ["upload", "search", "ask", "cross"]] == [201, 200, 200, 404]
    assert data["identical_404"] and len(data["audited_denials"]) >= 2
    for row in data["audited_denials"]:
        assert {
            "actor",
            "timestamp",
            "operation",
            "object",
            "result",
            "skill_id",
            "usage_and_duration",
        } <= set(row)


def test_review_and_risk_records():
    for name in ["review-05.md", "review-06.md", "review-07.md"]:
        text = (ROOT / "reports" / name).read_text()
        assert all(word in text for word in ["手段", "查了什么", "判据", "结果"])
    for name in ["risk-concurrency.md", "risk-transaction.md", "risk-authz.md"]:
        text = (ROOT / "reports" / name).read_text()
        assert "实际" in text and "判定" in text


def test_report_links_resolve():
    for file in [ROOT / "report.md", ROOT / "reports/bench.md", ROOT / "reports/traceability.md"]:
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (file.parent / target.split("#")[0]).exists(), target


def test_actual_lease_renewal_and_worker_crash():
    data = load("lease-crash.json")
    assert data["workers_killed"] == 2 and data["live_after_35_seconds"] == 1
    assert data["after_worker_crash"] == 0 and data["business_rows"] == 0
    assert 0 <= data["clear_seconds_after_crash"] <= 30
