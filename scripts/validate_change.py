#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "openspec" / "changes" / "archive"
REQUIRED_SECTIONS = ("为什么", "本次做到哪", "本次不做", "与既有约定")
SCENARIO_TERMS = ("前置条件", "操作", "可观测结果")


def validate_change(change: Path) -> list[str]:
    errors: list[str] = []
    for filename in ("proposal.md", "design.md", "tasks.md"):
        if not (change / filename).is_file():
            errors.append(f"{change.name}: missing {filename}")

    proposal = (change / "proposal.md").read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        if section not in proposal:
            errors.append(f"{change.name}: proposal missing section {section}")

    design = (change / "design.md").read_text(encoding="utf-8")
    if "关键取舍" not in design:
        errors.append(f"{change.name}: design missing 关键取舍")

    specs = sorted((change / "specs").glob("*/spec.md"))
    if not specs:
        errors.append(f"{change.name}: no capability spec")
    for spec in specs:
        text = spec.read_text(encoding="utf-8")
        scenarios = re.findall(r"^### 场景：.+$", text, re.M)
        if not scenarios:
            errors.append(f"{spec.relative_to(change)}: no scenarios")
        for term in SCENARIO_TERMS:
            if term not in text:
                errors.append(f"{spec.relative_to(change)}: missing {term}")

    tasks = (change / "tasks.md").read_text(encoding="utf-8")
    if not re.search(r"^\d+\. \[[x ]\]", tasks, re.M):
        errors.append(f"{change.name}: tasks have no checklist items")
    if "[ ]" in tasks:
        errors.append(f"{change.name}: archived change has unfinished tasks")
    return errors


def main() -> int:
    if not CHANGES.is_dir():
        print("spec-check: no archived changes found", file=sys.stderr)
        return 1
    changes = [path for path in CHANGES.iterdir() if path.is_dir()]
    if not changes:
        print("spec-check: no archived changes found", file=sys.stderr)
        return 1

    errors = [error for change in changes for error in validate_change(change)]
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"spec-check: ok ({len(changes)} archived change)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
