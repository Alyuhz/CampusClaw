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
        "GLM_MODEL": environ.get("GLM_MODEL", "glm-4-flash").strip(),
        "GLM_TEMPERATURE": float(environ.get("GLM_TEMPERATURE", "0.1")),
        "GLM_TIMEOUT_SECONDS": int(environ.get("GLM_TIMEOUT_SECONDS", "15")),
        "SEARCH_RESULT_LIMIT": int(environ.get("SEARCH_RESULT_LIMIT", "5")),
        "MAX_UPLOAD_BYTES": int(environ.get("MAX_UPLOAD_BYTES", "1048576")),
        "TOKEN_TTL_SECONDS": int(environ.get("TOKEN_TTL_SECONDS", "28800")),
    }
    if supplied:
        config.update(supplied)

    database_path = Path(str(config["DATABASE_PATH"]))
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    config["DATABASE_PATH"] = database_path
    return config
