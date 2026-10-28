#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "campusclaw"
SQL_PATTERN = re.compile(
    r"""["']\s*(
        SELECT\b |
        INSERT\s+INTO\b |
        UPDATE\s+\w+\s+SET\b |
        DELETE\s+FROM\b |
        CREATE\s+TABLE\b |
        ALTER\s+TABLE\b |
        DROP\s+TABLE\b
    )""",
    flags=re.I | re.X,
)


def main() -> int:
    errors: list[str] = []
    required = [
        ROOT / "AGENTS.md",
        ROOT / "campusclaw" / "app.py",
        ROOT / "campusclaw" / "db.py",
        ROOT / "campusclaw" / "templates" / "index.html",
        ROOT / "tests" / "test_api.py",
        ROOT / "openspec" / "changes" / "archive",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required path: {path.relative_to(ROOT)}")

    for path in PACKAGE.glob("*.py"):
        if path.name == "db.py":
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SQL_PATTERN.search(line):
                errors.append(
                    f"SQL outside campusclaw/db.py: {path.relative_to(ROOT)}:{line_number}"
                )

    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("layout: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
