#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_SECRET = re.compile(
    r"^[ \t]*(FLASK_SECRET_KEY|JWT_SECRET_KEY|GLM_API_KEY|SEED_TEACHER_PASSWORD|"
    r"SEED_STUDENT_PASSWORD)[ \t]*=[ \t]*([^\s#]+)",
    re.M,
)
ENV_ASSIGNMENT = re.compile(r"^[ \t]*([A-Z][A-Z0-9_]*)[ \t]*=[ \t]*([^#\n]*)", re.M)
TOKEN_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
)
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".mdc",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PLAIN_NAMES = {".env.example", "Dockerfile", "Makefile", "pre-commit"}


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [ROOT / item for item in output.splitlines() if item]


def history_diff() -> str:
    return subprocess.run(
        ["git", "log", "-p", "--all", "--format="],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if not path.is_file() or (
            path.suffix not in TEXT_SUFFIXES and path.name not in PLAIN_NAMES
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.name == ".env.example":
            for match in ENV_ASSIGNMENT.finditer(text):
                if match.group(2).strip():
                    findings.append(f"non-empty value in example: {path.name}:{match.group(1)}")
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append(f"secret-like token in {path.relative_to(ROOT)}")

    history = history_diff()
    for pattern in TOKEN_PATTERNS:
        if pattern.search(history):
            findings.append("secret-like token found in Git history")
    for match in ENV_SECRET.finditer(history):
        if match.group(2).strip():
            findings.append(f"secret-like value in Git history: {match.group(1)}")

    for finding in findings:
        print(finding, file=sys.stderr)
    if findings:
        return 1
    print("secret-scan: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
