from pathlib import Path

import pytest

from campusclaw.config import ConfigurationError, load_config

BASE_ENV = {
    "FLASK_SECRET_KEY": "test-flask-secret",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "DATABASE_PATH": "instance/test.sqlite3",
    "APP_VERSION": "test",
    "SEED_TEACHER_PASSWORD": "teacher-pass",
    "SEED_STUDENT_PASSWORD": "student-pass",
    "GLM_MODEL": "glm-test",
    "GLM_TEMPERATURE": "0.1",
    "GLM_TIMEOUT_SECONDS": "15",
    "SEARCH_RESULT_LIMIT": "5",
    "MAX_UPLOAD_BYTES": "1048576",
    "TOKEN_TTL_SECONDS": "3600",
}


@pytest.mark.parametrize("missing_key", BASE_ENV)
def test_each_required_configuration_fails_fast(monkeypatch, missing_key):
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing_key)

    with pytest.raises(ConfigurationError, match=missing_key):
        load_config()


def test_env_example_contains_only_blank_values():
    assignments = {}
    for line in Path(".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        assert separator == "="
        assignments[key] = value

    assert set(BASE_ENV) | {"WEB_PORT", "GLM_API_KEY"} == set(assignments)
    assert all(value == "" for value in assignments.values())
