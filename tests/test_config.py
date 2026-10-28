import pytest

from campusclaw.config import ConfigurationError, load_config


def test_missing_required_configuration_fails_fast(monkeypatch):
    for key in (
        "FLASK_SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_PATH",
        "APP_VERSION",
        "SEED_TEACHER_PASSWORD",
        "SEED_STUDENT_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ConfigurationError, match="FLASK_SECRET_KEY"):
        load_config()
