from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when a required external configuration value is missing."""


def _required(environ: dict[str, str], key: str) -> str:
    value = environ.get(key, "").strip()
    if not value:
        raise ConfigurationError(f"missing required environment variable: {key}")
    return value


def load_config(test_config: dict[str, Any] | None = None) -> dict[str, Any]:
    environ = dict(os.environ)
    supplied = test_config or {}

    def required(key: str, environment_key: str) -> str:
        value = supplied.get(key)
        if value is not None and str(value).strip():
            return str(value)
        return _required(environ, environment_key)

    config: dict[str, Any] = {
        "SECRET_KEY": required("SECRET_KEY", "FLASK_SECRET_KEY"),
        "JWT_SECRET": required("JWT_SECRET", "JWT_SECRET_KEY"),
        "DATABASE_PATH": required("DATABASE_PATH", "DATABASE_PATH"),
        "APP_VERSION": required("APP_VERSION", "APP_VERSION"),
        "SEED_TEACHER_PASSWORD": required("SEED_TEACHER_PASSWORD", "SEED_TEACHER_PASSWORD"),
        "SEED_STUDENT_PASSWORD": required("SEED_STUDENT_PASSWORD", "SEED_STUDENT_PASSWORD"),
        "GLM_API_KEY": environ.get("GLM_API_KEY", "").strip(),
        "GLM_MODEL": required("GLM_MODEL", "GLM_MODEL"),
        "GLM_TEMPERATURE": float(required("GLM_TEMPERATURE", "GLM_TEMPERATURE")),
        "GLM_TIMEOUT_SECONDS": int(required("GLM_TIMEOUT_SECONDS", "GLM_TIMEOUT_SECONDS")),
        "SEARCH_RESULT_LIMIT": int(required("SEARCH_RESULT_LIMIT", "SEARCH_RESULT_LIMIT")),
        "MAX_UPLOAD_BYTES": int(required("MAX_UPLOAD_BYTES", "MAX_UPLOAD_BYTES")),
        "TOKEN_TTL_SECONDS": int(required("TOKEN_TTL_SECONDS", "TOKEN_TTL_SECONDS")),
    }
    if supplied:
        config.update(supplied)

    database_path = Path(str(config["DATABASE_PATH"]))
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    config["DATABASE_PATH"] = database_path
    return config
