from __future__ import annotations

from collections.abc import Callable

import pytest

from campusclaw import create_app


@pytest.fixture()
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-flask-secret",
            "JWT_SECRET": "test-jwt-secret",
            "DATABASE_PATH": tmp_path / "test.sqlite3",
            "APP_VERSION": "test",
            "SEED_TEACHER_PASSWORD": "teacher-pass",
            "SEED_STUDENT_PASSWORD": "student-pass",
            "GLM_API_KEY": "",
            "GLM_MODEL": "glm-test",
            "GLM_TEMPERATURE": 0.1,
            "GLM_TIMEOUT_SECONDS": 15,
            "SEARCH_RESULT_LIMIT": 5,
            "MAX_UPLOAD_BYTES": 1_048_576,
            "TOKEN_TTL_SECONDS": 3600,
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client) -> Callable[[str], dict[str, str]]:
    def do_login(username: str) -> dict[str, str]:
        password = "teacher-pass" if username.startswith("teacher") else "student-pass"
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        token = response.get_json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}

    return do_login
