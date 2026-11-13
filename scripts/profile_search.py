from __future__ import annotations

import cProfile
import json
import secrets
import tempfile
from pathlib import Path

from scripts.bench import seed_database
from scripts.delivery_common import ROOT


def main():
    from campusclaw import create_app
    from campusclaw.search import search

    with tempfile.TemporaryDirectory(prefix="campusclaw-profile-") as temp:
        env = {
            key: secrets.token_urlsafe(32)
            for key in [
                "FLASK_SECRET_KEY",
                "JWT_SECRET_KEY",
                "SEED_TEACHER_PASSWORD",
                "SEED_STUDENT_PASSWORD",
            ]
        }
        database = Path(temp) / "profile.sqlite3"
        seed_database(database, env)
        app = create_app(
            {
                "TESTING": True,
                "COOKIE_SECURE": False,
                "TELEMETRY_ENABLED": False,
                "GLM_API_KEY": "",
                "DATABASE_PATH": str(database),
                "APP_VERSION": "profile",
                "SECRET_KEY": env["FLASK_SECRET_KEY"],
                "JWT_SECRET": env["JWT_SECRET_KEY"],
                "SEED_TEACHER_PASSWORD": env["SEED_TEACHER_PASSWORD"],
                "SEED_STUDENT_PASSWORD": env["SEED_STUDENT_PASSWORD"],
            }
        )
        result = {}
        for enabled in [False, True]:
            app.config["SEARCH_CACHE_ENABLED"] = enabled
            with app.app_context():
                search("class-a", "事务隔离 数据库 并发 教学", 8)
                profiler = cProfile.Profile()
                profiler.enable()
                for _ in range(100):
                    assert len(search("class-a", "事务隔离 数据库 并发 教学", 8)) == 8
                profiler.disable()
                rows = []
                for entry in sorted(profiler.getstats(), key=lambda e: e.totaltime, reverse=True)[
                    :15
                ]:
                    code = entry.code
                    name = (
                        code
                        if isinstance(code, str)
                        else Path(code.co_filename).name + ":" + code.co_name
                    )
                    rows.append(
                        {
                            "function": name,
                            "calls": entry.callcount,
                            "cumulative_seconds": entry.totaltime,
                            "inline_seconds": entry.inlinetime,
                        }
                    )
                result["cache-on" if enabled else "cache-off"] = rows
        (ROOT / "reports/lesson10/search-profile.json").write_text(
            json.dumps(
                {
                    "kind": "isolated search path cProfile, not HTTP capacity",
                    "calls_each": 100,
                    "top_functions": result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print("Real FTS/cache path profiles captured.")


if __name__ == "__main__":
    main()
