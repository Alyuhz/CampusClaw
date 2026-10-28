from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import Flask, render_template

from . import assistant, auth, materials, search
from .config import load_config
from .db import close_db, database_is_ready, init_db
from .http import api_response, configure_logging, register_http


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(load_config(test_config))
    app.config["MAX_CONTENT_LENGTH"] = int(app.config["MAX_UPLOAD_BYTES"]) + 65_536
    app.json.ensure_ascii = False
    configure_logging(app)

    app.teardown_appcontext(close_db)
    init_db(app)
    register_http(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(materials.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(assistant.bp)

    @app.get("/health")
    def health() -> tuple:
        database_status = "ok" if database_is_ready() else "unavailable"
        status = 200 if database_status == "ok" else 503
        return api_response(
            {
                "status": "ok" if status == 200 else "degraded",
                "version": app.config["APP_VERSION"],
                "time": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "dependencies": {"database": database_status},
            },
            status=status,
        )

    @app.get("/")
    def index() -> str:
        return render_template("index.html", version=app.config["APP_VERSION"])

    return app
