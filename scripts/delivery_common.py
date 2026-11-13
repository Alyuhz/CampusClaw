from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_snapshot() -> dict:
    paths = set()
    for pattern in (
        "campusclaw/**/*",
        "scripts/*.py",
        "tests/*.py",
        "apitest/cases/*.py",
        "monitoring/**/*",
    ):
        paths.update(
            p
            for p in ROOT.glob(pattern)
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    paths.update(
        ROOT / p
        for p in (
            "Dockerfile",
            ".dockerignore",
            "compose.yaml",
            "Makefile",
            "requirements.lock",
            "requirements-dev.lock",
            "pyproject.toml",
            "conftest.py",
            ".github/workflows/check.yml",
        )
    )
    files = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
        if p.exists()
    }
    return {
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "state": "local worktree",
        "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "files": files,
    }


class Client:
    """One origin and one caller per client; persistent transport, no automatic write retries."""

    def __init__(self, url: str):
        from http.cookies import SimpleCookie
        from urllib.parse import urlsplit

        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Expected HTTP(S) URL")
        self.url = url.rstrip("/")
        self.host, self.port, self.scheme = parsed.hostname, parsed.port, parsed.scheme
        self.connection = None
        self.cookies = SimpleCookie()
        self.token = ""
        self.last_csrf_ms = 0.0

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def _send(self, path, method, body, headers):
        import http.client

        hdr = dict(headers)
        if self.token:
            hdr.setdefault("Authorization", "Bearer " + self.token)
        cookie = "; ".join(
            m.OutputString(attrs=[])
            for m in self.cookies.values()
            if not m["secure"] or self.scheme == "https"
        )
        if cookie:
            hdr["Cookie"] = cookie
        for attempt in range(2):
            if self.connection is None:
                cls = (
                    http.client.HTTPSConnection
                    if self.scheme == "https"
                    else http.client.HTTPConnection
                )
                self.connection = cls(self.host, self.port, timeout=30)
            try:
                self.connection.request(method, path, body=body, headers=hdr)
                response = self.connection.getresponse()
                raw = response.read()
                for key, value in response.getheaders():
                    if key.lower() == "set-cookie":
                        self.cookies.load(value)
                status = response.status
                if response.will_close:
                    self.close()
                try:
                    data = json.loads(raw) if raw else {}
                except ValueError:
                    data = {"non_json_response": True}
                return status, data
            except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError):
                self.close()
                if method != "GET" or attempt:
                    raise
        raise RuntimeError("Transport retry exhausted")

    def request(
        self, path: str, method: str = "GET", payload=None, headers=None
    ) -> tuple[int, dict]:
        hdr = dict(headers or {})
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            hdr["Content-Type"] = "application/json"
        return self._send(path, method, body, hdr)

    def login(self, user: str, password: str) -> None:
        status, data = self.request(
            "/api/v1/auth/login", "POST", {"username": user, "password": password}
        )
        if status != 200:
            raise RuntimeError(f"Login failed: {status}")
        self.token = data["data"]["token"]

    def upload(self, title: str, content: str) -> tuple[int, dict]:
        started = time.monotonic()
        status, data = self.request("/api/v1/auth/csrf")
        self.last_csrf_ms = (time.monotonic() - started) * 1000
        if status != 200:
            return status, data
        boundary = "CampusClawBoundary"
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\n{title}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.md"\r\n'
            f"Content-Type: text/markdown\r\n\r\n{content}\r\n--{boundary}--\r\n"
        ).encode()
        return self._send(
            "/api/v1/materials",
            "POST",
            body,
            {
                "X-CSRF-Token": data["data"]["csrf_token"],
                "Content-Type": "multipart/form-data; boundary=" + boundary,
            },
        )
