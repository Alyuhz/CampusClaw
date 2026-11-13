import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Receiver(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 65536:
            self.send_error(413)
            return
        data = json.loads(self.rfile.read(size))
        safe = {
            "received_at": time.time(),
            "status": data.get("status"),
            "alerts": [
                {
                    "status": a.get("status"),
                    "labels": {
                        k: v
                        for k, v in a.get("labels", {}).items()
                        if k in {"alertname", "capability", "severity"}
                    },
                    "startsAt": a.get("startsAt"),
                    "endsAt": a.get("endsAt"),
                    "annotations": {"dashboard": a.get("annotations", {}).get("dashboard")},
                }
                for a in data.get("alerts", [])
            ],
        }
        path = Path("/evidence")
        path.mkdir(exist_ok=True)
        with (path / "notifications.jsonl").open("a") as output:
            output.write(json.dumps(safe) + "\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Receiver).serve_forever()
