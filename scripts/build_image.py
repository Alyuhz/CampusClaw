from __future__ import annotations

import json
import os
import re
import subprocess

from scripts.delivery_common import ROOT, source_snapshot


def main():
    snapshot = source_snapshot()
    revision = os.environ.get("SOURCE_REVISION", "")
    if revision:
        if not re.fullmatch("[0-9a-f]{40}", revision) or revision != snapshot["base_commit"]:
            raise ValueError("SOURCE_REVISION must be the full actual checked-out SHA")
        changed = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "HEAD",
                "--",
                "campusclaw",
                "Dockerfile",
                ".dockerignore",
                "requirements.lock",
            ],
            cwd=ROOT,
            text=True,
        ).strip()
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "campusclaw"],
            cwd=ROOT,
            text=True,
        ).strip()
        if changed or untracked:
            raise ValueError("Dirty runtime cannot be tagged as clean commit")
        snapshot["state"] = "clean commit"
    else:
        revision = "worktree-" + snapshot["sha256"][:16]
    image = "campusclaw:" + revision
    subprocess.run(
        ["docker", "build", "--build-arg", "SOURCE_REVISION=" + revision, "-t", image, "."],
        cwd=ROOT,
        check=True,
    )
    info = json.loads(subprocess.check_output(["docker", "image", "inspect", image], text=True))[0]
    out = ROOT / "reports/lesson10"
    out.mkdir(exist_ok=True)
    (out / "build.json").write_text(
        json.dumps(
            {
                "image": image,
                "image_id": info["Id"],
                "revision": revision,
                "source": snapshot,
                "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            },
            indent=2,
        )
    )
    if os.environ.get("GITHUB_ACTIONS") == "true":
        subprocess.run(["docker", "save", "-o", str(out / "image.tar"), image], check=True)
    print(image)


if __name__ == "__main__":
    main()
