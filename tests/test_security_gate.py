from __future__ import annotations

import subprocess
import sys

import pytest

from scripts.dependency_audit import evaluate


@pytest.mark.parametrize(
    "exception",
    [
        [],
        [
            {
                "package": "demo",
                "version": "1",
                "id": "CVE-test",
                "reason": "temporary",
                "mitigation": "isolated",
                "owner": "team",
                "expires": "2000-01-01",
            }
        ],
    ],
)
def test_unhandled_or_expired_exception_blocks(exception):
    report = {"dependencies": [{"name": "demo", "version": "1", "vulns": [{"id": "CVE-test"}]}]}
    if not exception:
        assert evaluate(report, exception) == ["demo==1:CVE-test"]
    else:
        with pytest.raises(ValueError, match="Expired"):
            evaluate(report, exception)


def test_exact_exception_and_no_silent_match():
    report = {"dependencies": [{"name": "demo", "version": "1", "vulns": [{"id": "CVE-test"}]}]}
    entry = {
        "package": "demo",
        "version": "1",
        "id": "CVE-test",
        "reason": "temporary",
        "mitigation": "isolated",
        "owner": "team",
        "expires": "2099-01-01",
    }
    assert evaluate(report, [entry]) == []
    with pytest.raises(ValueError):
        evaluate(report, [{**entry, "id": "wrong"}])
    assert evaluate({"dependencies": [{"name": "demo", "version": "1", "vulns": []}]}, []) == []


def test_dependency_tool_failure_blocks(monkeypatch, tmp_path):
    from scripts import dependency_audit

    monkeypatch.setattr(sys, "argv", ["audit", "--root", str(tmp_path)])

    def fail(*args, **kwargs):
        return subprocess.CompletedProcess([], 2, "", "offline")

    monkeypatch.setattr(subprocess, "run", fail)
    assert dependency_audit.main() == 2


def test_secret_in_deleted_history_is_detected_without_echo(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
        )

    git("init", "-q")
    path = tmp_path / ".env.example"
    path.write_text("JWT_SECRET_KEY=synthetic-history-value\n")
    git("add", ".env.example")
    git(
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    path.write_text("JWT_SECRET_KEY=\n")
    git("add", ".env.example")
    git(
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "remove",
    )
    run = subprocess.run(
        [sys.executable, "scripts/secret_scan.py", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 1
    assert "Git history" in run.stderr
    assert "synthetic-history-value" not in run.stderr


def test_model_key_length_is_enforced(monkeypatch):
    from campusclaw.config import ConfigurationError, load_config

    cfg = {
        "SECRET_KEY": "test-only",
        "JWT_SECRET": "short",
        "DATABASE_PATH": "/tmp/unused",
        "APP_VERSION": "test",
        "SEED_TEACHER_PASSWORD": "test",
        "SEED_STUDENT_PASSWORD": "test",
    }
    with pytest.raises(ConfigurationError, match="32 bytes"):
        load_config(cfg)
