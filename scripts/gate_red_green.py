from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.delivery_common import ROOT, source_snapshot


def main():
    evidence = ROOT / "reports/lesson10/gate"
    evidence.mkdir(parents=True, exist_ok=True)
    snapshot = source_snapshot()
    with tempfile.TemporaryDirectory(prefix="campusclaw-gate-") as temp:
        target = Path(temp) / "project"
        shutil.copytree(
            ROOT,
            target,
            ignore=shutil.ignore_patterns(
                ".venv",
                "instance",
                "__pycache__",
                ".pytest_cache",
                ".ruff_cache",
                ".env",
                "bench",
                "bench-pilot-interrupted",
                "bench-short-connection-failed",
            ),
        )
        # Copy includes an isolated Git history for the scanner; no new project commits are made.
        os.symlink(ROOT / ".venv", target / ".venv", target_is_directory=True)
        # Only summary artifacts are needed by evidence-integrity tests, not raw load samples.
        bench = target / "reports/lesson10/bench"
        bench.mkdir(parents=True, exist_ok=True)
        for name in ("results.json", "analysis.json", "manifest.json", "environment.json"):
            source = ROOT / "reports/lesson10/bench" / name
            if source.exists():
                shutil.copyfile(source, bench / name)

        file = target / "tests/test_api.py"
        original = file.read_text()
        wrong = original.replace(
            "assert response.status_code == 200", "assert response.status_code == 299", 1
        )
        assert wrong != original
        (evidence / "mutation.diff").write_text(
            "".join(
                difflib.unified_diff(
                    original.splitlines(True),
                    wrong.splitlines(True),
                    fromfile="tests/test_api.py",
                    tofile="tests/test_api.py",
                )
            )
        )
        results = []
        for phase, content in [("red", wrong), ("green", original)]:
            file.write_text(content)
            run = subprocess.run(
                ["make", "check"],
                cwd=target,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            (evidence / (phase + ".txt")).write_text(run.stdout)
            results.append(
                {
                    "phase": phase,
                    "command": "make check",
                    "exit_code": run.returncode,
                    "time": datetime.now(UTC).isoformat(),
                }
            )
        assert results[0]["exit_code"] != 0 and "299" in (evidence / "red.txt").read_text()
        assert results[1]["exit_code"] == 0
        assert file.read_text() == original
        (evidence / "result.json").write_text(
            json.dumps(
                {
                    "runs": results,
                    "source": snapshot,
                    "project_commits_created": False,
                    "main_worktree_untouched": True,
                },
                indent=2,
            )
        )
    print("Deliberately broken assertion blocked; restored same command is green.")


if __name__ == "__main__":
    main()
