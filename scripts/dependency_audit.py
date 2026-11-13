#!/usr/bin/env python3
"""Audit both pinned dependency sets. All known unregistered vulnerabilities block."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


def evaluate(report: dict, exceptions: list[dict]) -> list[str]:
    blocked = []
    used = set()
    for dep in report["dependencies"]:
        for vuln in dep.get("vulns", []):
            match = None
            for i, entry in enumerate(exceptions):
                required = {"package", "version", "id", "reason", "mitigation", "owner", "expires"}
                if required - entry.keys() or not all(str(entry[k]).strip() for k in required):
                    raise ValueError("Incomplete vulnerability exception")
                expiry = date.fromisoformat(entry["expires"])
                if expiry < date.today():
                    raise ValueError("Expired vulnerability exception")
                if (entry["package"].lower(), entry["version"], entry["id"]) == (
                    dep["name"].lower(),
                    dep["version"],
                    vuln["id"],
                ):
                    match = i
            if match is None:
                blocked.append(f"{dep['name']}=={dep['version']}:{vuln['id']}")
            else:
                used.add(match)
    if set(range(len(exceptions))) != used:
        raise ValueError("Unmatched vulnerability exception")
    return sorted(set(blocked))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        command = [
            sys.executable,
            "-m",
            "pip_audit",
            "--no-deps",
            "--disable-pip",
            "--progress-spinner",
            "off",
            "--timeout",
            "20",
            "-f",
            "json",
        ]
        for lock in ("requirements.lock", "requirements-dev.lock"):
            command += ["-r", str(args.root / lock)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if run.returncode not in (0, 1):
            raise ValueError("Dependency audit tool error")
        report = json.loads(run.stdout)
        if not isinstance(report.get("dependencies"), list) or not report["dependencies"]:
            raise ValueError("Missing dependency report")
        # Failed/skipped packages are not a green audit.
        if any("skip_reason" in dep for dep in report["dependencies"]):
            raise ValueError("Dependency was skipped")
        path = args.root / "security-exceptions.json"
        exceptions = json.loads(path.read_text()) if path.exists() else []
        blocked = evaluate(report, exceptions)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        for finding in blocked:
            print(finding)
        print(
            f"dependency-audit: {'FAIL' if blocked else 'ok'}; "
            f"unhandled={len(blocked)}, exceptions={len(exceptions)}"
        )
        return int(bool(blocked))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"dependency-audit: unavailable/invalid ({type(error).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
