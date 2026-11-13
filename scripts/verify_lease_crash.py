from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request

from scripts.delivery_common import ROOT
from scripts.delivery_runtime import Runtime


def inflight(runtime):
    req = urllib.request.Request(
        runtime.url + "/internal/metrics",
        headers={"Authorization": "Bearer " + runtime.config["METRICS_TOKEN"]},
    )
    with urllib.request.urlopen(req) as response:
        text = response.read().decode()
    line = next(
        line
        for line in text.splitlines()
        if line.startswith('capability_inflight{capability="materials-upload"}')
    )
    return int(float(line.rsplit(" ", 1)[1]))


def main():
    runtime = Runtime()
    stop = threading.Event()
    connection = None
    writer = None
    try:
        runtime.start()
        c = runtime.client()
        _, csrf = c.request("/api/v1/auth/csrf")
        cookie = "; ".join(m.OutputString(attrs=[]) for m in c.cookies.values())
        port = int(runtime.config["WEB_PORT"])
        connection = socket.create_connection(("127.0.0.1", port))
        headers = (
            f"POST /api/v1/materials HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            f"Authorization: Bearer {c.token}\r\n"
            f"Cookie: {cookie}\r\nX-CSRF-Token: {csrf['data']['csrf_token']}\r\n"
            "Content-Type: multipart/form-data; boundary=SlowBody\r\n"
            "Content-Length: 900000\r\nConnection: close\r\n\r\n"
        )
        connection.sendall(
            headers.encode()
            + b'--SlowBody\r\nContent-Disposition: form-data; name="file"; filename="slow.md"\r\n'
            b"Content-Type: text/markdown\r\n\r\n"
        )

        def feed():
            while not stop.wait(2):
                try:
                    connection.sendall(b"a" * 512)
                except OSError:
                    return

        writer = threading.Thread(target=feed, daemon=True)
        writer.start()
        for _ in range(30):
            if inflight(runtime) == 1:
                break
            time.sleep(0.2)
        assert inflight(runtime) == 1
        time.sleep(35)
        assert inflight(runtime) == 1, "live request lease did not renew"
        # Kill only the two workers inside this isolated temporary container, never the host.
        code = """import os,signal,json
from pathlib import Path
pids=[]
for path in Path('/proc').iterdir():
 if path.name.isdigit():
  try:
   status=(path/'status').read_text()
   if '\\nPPid:\\t1\\n' in status and b'gunicorn' in (path/'cmdline').read_bytes():
    pids.append(int(path.name))
  except OSError:pass
assert len(pids)==2,pids
for pid in pids:os.kill(pid,signal.SIGKILL)
print(json.dumps({'workers_killed':len(pids)}))
"""
        result = json.loads(runtime.app_exec("python", "-c", code))
        killed = time.monotonic()
        stop.set()
        connection.close()
        connection = None
        runtime.wait(runtime.url + "/ready")
        cleared = None
        for _ in range(70):
            if inflight(runtime) == 0:
                cleared = time.monotonic() - killed
                break
            time.sleep(0.5)
        assert cleared is not None and cleared <= 30
        status, data = runtime.client().request("/api/v1/materials")
        assert status == 200 and data["data"]["items"] == []
        result.update(
            {
                "live_after_35_seconds": 1,
                "after_worker_crash": 0,
                "clear_seconds_after_crash": cleared,
                "business_rows": 0,
                "scope": "isolated temporary compose only",
            }
        )
        (ROOT / "reports/lesson10/lease-crash.json").write_text(json.dumps(result, indent=2))
        print(result)
    finally:
        stop.set()
        if connection:
            connection.close()
        if writer:
            writer.join(timeout=3)
        runtime.close()


if __name__ == "__main__":
    main()
