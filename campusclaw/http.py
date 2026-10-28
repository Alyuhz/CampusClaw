from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from flask import Flask, Response, g, jsonify, request


class ApiError(Exception):
    def __init__(self, *, code: int, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def api_response(data: Any, *, code: int = 0, message: str = "ok", status: int = 200) -> tuple:
    return jsonify({"code": code, "message": message, "data": data}), status


def not_found() -> ApiError:
    return ApiError(code=1304, message="资源不存在", status=404)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "module": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False

    # The application access log is the single structured request record. Keeping
    # Werkzeug's default access logger would emit a duplicate plain-text line.
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.disabled = True


def register_http(app: Flask) -> None:
    @app.before_request
    def assign_request_id() -> None:
        supplied = request.headers.get("X-Request-ID", "")
        if re.fullmatch(r"[A-Za-z0-9-]{8,64}", supplied):
            g.request_id = supplied
        else:
            g.request_id = uuid.uuid4().hex
        g.started_at = time.monotonic()

    @app.after_request
    def finish_request(response: Response) -> Response:
        request_id = getattr(g, "request_id", uuid.uuid4().hex)
        response.headers["X-Request-ID"] = request_id
        started_at = getattr(g, "started_at", time.monotonic())
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)
        app.logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple:
        return api_response(None, code=error.code, message=error.message, status=error.status)

    @app.errorhandler(404)
    def handle_404(_error: Exception) -> tuple:
        return api_response(None, code=1304, message="资源不存在", status=404)

    @app.errorhandler(405)
    def handle_405(_error: Exception) -> tuple:
        return api_response(None, code=1105, message="请求方法不允许", status=405)

    @app.errorhandler(413)
    def handle_413(_error: Exception) -> tuple:
        return api_response(None, code=1103, message="请求超过大小上限", status=413)

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception) -> tuple:
        app.logger.exception("unhandled error")
        return api_response(None, code=1500, message="系统错误", status=500)
