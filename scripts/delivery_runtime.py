from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from scripts.delivery_common import ROOT, Client


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Runtime:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="campusclaw-delivery-")
        self.path = Path(self.temp.name)
        self.project = "cc10-" + uuid.uuid4().hex[:10]
        for name in ["campusclaw", "monitoring"]:
            shutil.copytree(
                ROOT / name, self.path / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        for name in ["Dockerfile", ".dockerignore", "requirements.lock", "compose.yaml"]:
            shutil.copyfile(ROOT / name, self.path / name)
        self.config = {
            "FLASK_SECRET_KEY": secrets.token_urlsafe(32),
            "JWT_SECRET_KEY": secrets.token_urlsafe(32),
            "SEED_TEACHER_PASSWORD": secrets.token_urlsafe(24),
            "SEED_STUDENT_PASSWORD": secrets.token_urlsafe(24),
            "METRICS_TOKEN": secrets.token_urlsafe(32),
            "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
            "DATABASE_PATH": "/app/instance/lesson10.sqlite3",
            "APP_VERSION": "lesson10",
            "COOKIE_SECURE": "false",
            "TELEMETRY_ENABLED": "true",
            "SEARCH_CACHE_ENABLED": "true",
            "IMAGE_TAG": "lesson10-local",
            "WEB_PORT": str(free_port()),
            "PROMETHEUS_PORT": str(free_port()),
            "GRAFANA_PORT": str(free_port()),
            "ALERTMANAGER_PORT": str(free_port()),
        }
        alerts = self.path / "monitoring/alerts.yml"
        alerts.write_text(
            alerts.read_text().replace(
                "http://localhost:3000", "http://127.0.0.1:" + self.config["GRAFANA_PORT"]
            )
        )
        env_file = self.path / ".env"
        env_file.write_text("\n".join(k + "=" + v for k, v in self.config.items()) + "\n")
        env_file.chmod(0o600)
        self.env = {**os.environ, **self.config}
        self.url = "http://127.0.0.1:" + self.config["WEB_PORT"]
        self.prom = "http://127.0.0.1:" + self.config["PROMETHEUS_PORT"]
        self.grafana = "http://127.0.0.1:" + self.config["GRAFANA_PORT"]

    def compose(self, *args, check=True):
        return subprocess.run(
            [
                "docker",
                "compose",
                "--project-name",
                self.project,
                "--project-directory",
                str(self.path),
                *args,
            ],
            env=self.env,
            capture_output=True,
            text=True,
            check=check,
        )

    def start(self):
        self.compose("config", "--quiet")
        result = self.compose("up", "-d", "--build")
        self.wait(self.url + "/ready")
        return result

    @staticmethod
    def wait(url, timeout=180):
        import urllib.request

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            time.sleep(0.5)
        raise RuntimeError("Readiness deadline exceeded")

    def client(self, username="teacher-a"):
        client = Client(self.url)
        client.login(
            username,
            self.config[
                "SEED_TEACHER_PASSWORD"
                if username.startswith("teacher")
                else "SEED_STUDENT_PASSWORD"
            ],
        )
        return client

    def close(self):
        self.compose("--profile", "telemetry", "down", "--volumes", "--remove-orphans", check=False)
        self.temp.cleanup()

    def app_exec(self, *args):
        return self.compose("exec", "-T", "app", *args).stdout


def runtime_flow(runtime: Runtime) -> dict:
    teacher = runtime.client()
    status, body = teacher.upload("课堂资料", "事务隔离 班级知识验证")
    assert status == 201
    material_id = body["data"]["id"]
    assert teacher.request(f"/api/v1/materials/{material_id}")[0] == 200
    other = runtime.client("student-b")
    cross = other.request(f"/api/v1/materials/{material_id}")
    missing = other.request("/api/v1/materials/999999")
    assert cross[0] == missing[0] == 404 and cross[1] == missing[1]
    runtime.compose("restart", "app")
    runtime.wait(runtime.url + "/ready")
    assert teacher.request(f"/api/v1/materials/{material_id}")[0] == 200
    uid = runtime.app_exec("id", "-u").strip()
    assert uid != "0"
    source = runtime.app_exec(
        "python",
        "-c",
        "from pathlib import Path; import json; "
        "print(json.dumps([str(p) for p in Path('/app/campusclaw').rglob('*.py')]))",
    )
    assert json.loads(source) == []
    assert (
        runtime.app_exec(
            "python",
            "-c",
            "from campusclaw.assistant import PROMPT_PATH; "
            "assert PROMPT_PATH.is_file(); print('prompt-ok')",
        ).strip()
        == "prompt-ok"
    )
    runtime.app_exec(
        "python",
        "-c",
        "import os; os.rename('/app/instance/lesson10.sqlite3','/app/instance/lesson10.saved')",
    )
    try:
        failed = teacher.request("/ready")[0]
        assert failed == 503
    finally:
        runtime.app_exec(
            "python",
            "-c",
            "import os; os.replace('/app/instance/lesson10.saved',"
            "'/app/instance/lesson10.sqlite3')",
        )
    assert teacher.request("/ready")[0] == 200
    build = json.loads(runtime.app_exec("cat", "/app/build-info.json"))
    return {
        "readiness_fault_sequence": [200, 503, 200],
        "prompt_resource": True,
        "upload": 201,
        "cross_class": 404,
        "missing": 404,
        "identical_404": True,
        "restart_data_retained": True,
        "uid": uid,
        "application_py_files": 0,
        "build_info": build,
    }
