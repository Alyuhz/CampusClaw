"""Reproducible isolated load experiment. Does not use real users or model services."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

from scripts.delivery_common import ROOT, Client, source_snapshot


def summary(samples: list[dict], seconds: float) -> dict:
    values = sorted(row["ms"] for row in samples)
    return {
        "samples": len(values),
        "throughput": len(values) / seconds,
        "p95_ms": values[max(0, math.ceil(0.95 * len(values)) - 1)] if values else None,
        "error_rate": sum(not row["ok"] for row in samples) / len(values) if values else 1,
    }


def seed_database(path: Path, env: dict, seed: int = 0) -> dict:
    from campusclaw import create_app, db

    app = create_app(
        {
            "TESTING": True,
            "COOKIE_SECURE": False,
            "DATABASE_PATH": str(path),
            "SECRET_KEY": env["FLASK_SECRET_KEY"],
            "JWT_SECRET": env["JWT_SECRET_KEY"],
            "APP_VERSION": "bench",
            "SEED_TEACHER_PASSWORD": env["SEED_TEACHER_PASSWORD"],
            "SEED_STUDENT_PASSWORD": env["SEED_STUDENT_PASSWORD"],
        }
    )
    app.logger.disabled = True
    # Exactly 200 materials per class and 20 chunks per material, generated deterministically.
    with app.app_context():
        for classroom in ("a", "b"):
            client = app.test_client()
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "teacher-" + classroom, "password": env["SEED_TEACHER_PASSWORD"]},
            )
            import jwt

            session = jwt.decode(
                response.get_json()["data"]["token"], app.config["JWT_SECRET"], algorithms=["HS256"]
            )["jti"]
            actor = db.get_user_by_username("teacher-" + classroom)
            for index in range(200):
                chunks = [
                    {
                        "chunk_index": chunk,
                        "content": ("事务隔离 数据库 并发 教学 唯一课程知识。" * 35)
                        + str(index)
                        + ":"
                        + str(chunk)
                        + (f" seed:{seed}" if seed else ""),
                        "start_line": chunk + 1,
                        "end_line": chunk + 1,
                    }
                    for chunk in range(20)
                ]
                db.create_material(
                    class_id="class-" + classroom,
                    title=f"material-{index}",
                    filename=f"{index}.md",
                    created_by=actor["id"],
                    chunks=chunks,
                    session_id=session,
                )
    return {
        "classes": 2,
        "materials_per_class": 200,
        "chunks_per_material": 20,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def run_case(
    url: str, endpoint: str, concurrency: int, warmup: float, duration: float, password: str
) -> list[dict]:
    deadline = {}

    def start_clock():
        start = time.monotonic()
        deadline.update(measure=start + warmup, end=start + warmup + duration)

    barrier = threading.Barrier(concurrency + 1, action=start_clock, timeout=60)

    def worker(index):
        client = Client(url)
        client.login("teacher-a", password)
        barrier.wait()
        rows = []
        while time.monotonic() < deadline["end"]:
            started = time.monotonic()
            try:
                if endpoint == "submit":
                    status, _ = client.upload("load", "事务隔离资料")
                elif endpoint == "query":
                    status, _ = client.request("/api/v1/materials/1")
                else:
                    status, _ = client.request(
                        "/api/v1/search?q=" + quote("事务隔离 数据库 并发 教学")
                    )
                ok = status == (201 if endpoint == "submit" else 200)
            except Exception:
                status = 0
                ok = False
            end = time.monotonic()
            if started >= deadline["measure"]:
                rows.append(
                    {
                        "ms": (end - started) * 1000,
                        "status": status,
                        "ok": ok,
                        "csrf_ms": getattr(client, "last_csrf_ms", 0)
                        if endpoint == "submit"
                        else 0,
                    }
                )
        client.close()
        return rows

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        jobs = [executor.submit(worker, index) for index in range(concurrency)]
        barrier.wait()
        return [row for job in jobs for row in job.result()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/lesson10/bench")
    parser.add_argument(
        "--duration", type=float, default=float(os.environ.get("BENCH_DURATION", "20"))
    )
    parser.add_argument("--warmup", type=float, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--concurrency", default="1,4,8,16,32")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    parameters = {
        "duration": args.duration,
        "seed": args.seed,
        "warmup": args.warmup,
        "repeats": args.repeats,
        "concurrency": [int(v) for v in args.concurrency.split(",")],
        "workers": 2,
        "threads_per_worker": 4,
        "model": "extractive",
        "telemetry": True,
        "upload_cost": "end-to-end includes csrf acquisition",
    }
    if args.duration <= 0 or args.warmup < 0 or args.repeats < 1:
        raise ValueError("Invalid load parameters")
    with tempfile.TemporaryDirectory(prefix="campusclaw-bench-") as temp:
        folder = Path(temp)
        env = {
            **os.environ,
            "FLASK_SECRET_KEY": secrets.token_urlsafe(32),
            "JWT_SECRET_KEY": secrets.token_urlsafe(32),
            "SEED_TEACHER_PASSWORD": secrets.token_urlsafe(24),
            "SEED_STUDENT_PASSWORD": secrets.token_urlsafe(24),
            "GLM_API_KEY": "",
            "COOKIE_SECURE": "false",
            "APP_VERSION": "lesson10-bench",
            "TELEMETRY_ENABLED": "true",
            "METRICS_TOKEN": secrets.token_urlsafe(32),
            "PYTHONPATH": str(ROOT),
        }
        seed = folder / "seed.sqlite3"
        dataset = seed_database(seed, env, args.seed)
        result = {
            "parameters": parameters,
            "data": dataset,
            "source": source_snapshot(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "cases": [],
        }
        (args.output / "manifest.json").write_text(
            json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2)
        )
        for variant in ("before", "after"):
            env["SEARCH_CACHE_ENABLED"] = "true" if variant == "after" else "false"
            for endpoint in ("search", "query", "submit"):
                for repeat in range(args.repeats):
                    for concurrency in parameters["concurrency"]:
                        live = folder / "live.sqlite3"
                        shutil.copyfile(seed, live)
                        env["DATABASE_PATH"] = str(live)
                        with socket.socket() as sock:
                            sock.bind(("127.0.0.1", 0))
                            port = sock.getsockname()[1]
                        log = open(folder / "server.log", "w")
                        process = subprocess.Popen(
                            [
                                sys.executable,
                                "-m",
                                "gunicorn",
                                "--bind",
                                f"127.0.0.1:{port}",
                                "--workers",
                                "2",
                                "--threads",
                                "4",
                                "--timeout",
                                "60",
                                "campusclaw:create_app()",
                            ],
                            cwd=ROOT,
                            env=env,
                            stdout=log,
                            stderr=log,
                        )
                        url = f"http://127.0.0.1:{port}"
                        try:
                            for _ in range(100):
                                if process.poll() is not None:
                                    raise RuntimeError("Benchmark server exited")
                                try:
                                    if Client(url).request("/ready")[0] == 200:
                                        break
                                except OSError:
                                    pass
                                time.sleep(0.1)
                            else:
                                raise RuntimeError("Benchmark server not ready")
                            samples = run_case(
                                url,
                                endpoint,
                                concurrency,
                                args.warmup,
                                args.duration,
                                env["SEED_TEACHER_PASSWORD"],
                            )
                            row = {
                                "variant": variant,
                                "endpoint": endpoint,
                                "repeat": repeat,
                                "concurrency": concurrency,
                                **summary(samples, args.duration),
                            }
                            result["cases"].append(row)
                            (
                                args.output / f"{variant}-{endpoint}-{repeat}-{concurrency}.json"
                            ).write_text(json.dumps({"summary": row, "samples": samples}))
                            (args.output / "results.json").write_text(json.dumps(result, indent=2))
                            print(json.dumps(row), flush=True)
                        finally:
                            process.terminate()
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            log.close()


if __name__ == "__main__":
    main()
