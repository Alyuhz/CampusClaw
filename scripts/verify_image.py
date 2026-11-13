import io
import json
import re
import secrets
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

root = Path.cwd()
ev = root / "reports/evidence"


def docker(*args, **kwargs):
    return subprocess.run(["docker", *args], check=True, capture_output=True, **kwargs)


with tempfile.TemporaryDirectory(prefix="campusclaw-image-") as temp:
    p = Path(temp)
    cfg = {
        "FLASK_SECRET_KEY": secrets.token_urlsafe(32),
        "JWT_SECRET_KEY": secrets.token_urlsafe(32),
        "SEED_TEACHER_PASSWORD": secrets.token_urlsafe(24),
        "SEED_STUDENT_PASSWORD": secrets.token_urlsafe(24),
        "DATABASE_PATH": "/app/instance/verify.sqlite3",
        "APP_VERSION": "lesson09",
        "COOKIE_SECURE": "false",
    }
    env = p / "config.env"
    env.write_text("\n".join(k + "=" + v for k, v in cfg.items()))
    container = None
    try:
        container = docker(
            "run",
            "-d",
            "--env-file",
            str(env),
            "-p",
            "127.0.0.1::8000",
            "campusclaw:lesson09-security",
            text=True,
        ).stdout.strip()
        ready = False
        for _ in range(25):
            state = json.loads(docker("inspect", container, text=True).stdout)[0]
            if not state["State"]["Running"]:
                break
            ports = state["NetworkSettings"]["Ports"].get("8000/tcp")
            if ports:
                url = "http://127.0.0.1:" + ports[0]["HostPort"] + "/health"
                try:
                    with urllib.request.urlopen(url, timeout=2) as response:
                        health = json.load(response)
                    ready = health["data"]["status"] == "ok"
                    if ready:
                        break
                except (OSError, ValueError):
                    pass
            time.sleep(0.4)
        logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
        (ev / "docker-runtime.txt").write_text(logs.stdout + logs.stderr)
        if not ready:
            print("Container health failed; see reports/evidence/docker-runtime.txt")
            raise SystemExit(1)
        info = json.loads(
            docker("image", "inspect", "campusclaw:lesson09-security", text=True).stdout
        )[0]
        uid = docker("exec", container, "id", "-u", text=True).stdout.strip()
        assert uid != "0"
        result = {
            "image_id": info["Id"],
            "user": info["Config"]["User"],
            "uid": uid,
            "health": health,
            "docker_server_version": docker(
                "version", "--format", "{{.Server.Version}}", text=True
            ).stdout.strip(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
        }
        # Scan all saved layers, including dependencies copied into the runtime image.
        archive = p / "image.tar"
        docker("save", "-o", str(archive), "campusclaw:lesson09-security")
        findings = []
        layers = []
        files = 0
        text_files = 0
        total_files = 0
        with tarfile.open(archive) as outer:
            names = outer.getnames()
            if "manifest.json" in names:
                manifest = json.load(outer.extractfile("manifest.json"))
                layer_paths = manifest[0]["Layers"]
            else:
                layer_paths = [name for name in names if name.endswith("/layer.tar")]
            for layer_path in layer_paths:
                layer_data = outer.extractfile(layer_path).read()
                layers.append(layer_path)
                with tarfile.open(fileobj=io.BytesIO(layer_data), mode="r:*") as layer:
                    for member in layer:
                        name = member.name.lstrip("./")
                        if not member.isfile():
                            continue
                        total_files += 1
                        if name.startswith(("app/", "build/")):
                            files += 1
                        if member.size > 8 * 1024 * 1024:
                            continue
                        if name.split("/")[-1] == ".env":
                            findings.append(name + ":dotenv")
                        data = layer.extractfile(member).read()
                        if any(
                            v.encode() in data
                            for k, v in cfg.items()
                            if k
                            in {
                                "FLASK_SECRET_KEY",
                                "JWT_SECRET_KEY",
                                "SEED_TEACHER_PASSWORD",
                                "SEED_STUDENT_PASSWORD",
                            }
                        ):
                            findings.append(name + ":test-env-value")
                        if b"\x00" not in data:
                            text_files += 1
                            if re.search(
                                rb"-----BEGIN (?:RSA |EC |OPENSSH )?"
                                rb"PRIVATE KEY-----\s+[A-Za-z0-9+/=]{20,}"
                                rb"|\bsk-[A-Za-z0-9_-]{20,}\b",
                                data,
                            ):
                                findings.append(name + ":secret-pattern")
        assert layers, "No saved image layers were scanned"
        result.update(
            {
                "layers_scanned": len(layers),
                "application_files_scanned": files,
                "application_secret_findings": findings,
                "text_files_scanned": text_files,
                "total_regular_files": total_files,
                "scope": (
                    "All saved runtime image layers: pattern scan on non-NUL files up to 8MiB; "
                    "generated test-secret matching on readable files up to 8MiB. "
                    "Binary/compressed artifacts are not claimed exhaustively inspected."
                ),
            }
        )
        assert files > 0
        assert not findings, findings
        (ev / "docker-verification.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            {
                k: result[k]
                for k in [
                    "image_id",
                    "uid",
                    "layers_scanned",
                    "application_files_scanned",
                    "application_secret_findings",
                ]
            }
        )
    finally:
        if container:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
