from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

from scripts.delivery_common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="campusclaw:lesson10-local")
    args = parser.parse_args()
    info = json.loads(
        subprocess.check_output(["docker", "image", "inspect", args.image], text=True)
    )[0]
    findings = []
    layers = 0
    files = 0
    business = []
    pattern = re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{20,}"
        rb"|\bsk-[A-Za-z0-9_-]{20,}\b"
    )
    with tempfile.TemporaryDirectory(prefix="campusclaw-layer-scan-") as temp:
        archive = Path(temp) / "image.tar"
        subprocess.run(["docker", "save", "-o", str(archive), args.image], check=True)
        with tarfile.open(archive) as outer:
            manifest = json.load(outer.extractfile("manifest.json"))
            for entry in manifest[0]["Layers"]:
                layers += 1
                with tarfile.open(
                    fileobj=io.BytesIO(outer.extractfile(entry).read()), mode="r:*"
                ) as layer:
                    for member in layer:
                        name = member.name.lstrip("./")
                        if not member.isfile() or member.size > 8 * 1024 * 1024:
                            continue
                        files += 1
                        data = layer.extractfile(member).read()
                        if name.startswith("app/campusclaw/"):
                            business.append(name)
                            if name.endswith(".py"):
                                findings.append(name + ":business-source")
                        if name.split("/")[-1] == ".env":
                            findings.append(name + ":dotenv")
                        if pattern.search(data):
                            findings.append(name + ":known-secret-pattern")
    assert layers and business
    assert not findings, findings
    out = {
        "image_id": info["Id"],
        "layers_scanned": layers,
        "bounded_files_scanned": files,
        "business_files_seen": len(business),
        "business_py_files": 0,
        "findings": findings,
        "scope": (
            "All saved layers; regular files <=8MiB; known token/private-key formats. "
            "Dependency and stdlib source is not claimed absent."
        ),
    }
    (ROOT / "reports/lesson10/image-scan.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
