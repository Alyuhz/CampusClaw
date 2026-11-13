import pytest

from campusclaw import db
from campusclaw.http import ApiError


def test_sec04_direct_student_write_denied(app):
    with app.app_context():
        student = db.get_user_by_username("student-a")
        with pytest.raises(ApiError) as denied:
            db.create_material(
                class_id="class-a",
                title="unauthorized",
                filename="x.md",
                created_by=student["id"],
                chunks=[],
            )
        assert denied.value.status == 401
        assert db.list_materials("class-a") == []


def test_csrf_required_with_valid_bearer(client, login):
    headers = login("teacher-a")
    headers.pop("X-CSRF-Token", None)
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 403


def test_audit_teacher_query_and_student_denial(client, login):
    student = login("student-a")
    assert client.post("/api/v1/materials", headers=student).status_code == 403
    teacher = login("teacher-a")
    response = client.get("/api/v1/audit-logs", headers=teacher)
    assert response.status_code == 200
    entries = response.get_json()["data"]["items"]
    assert any(e["actor"]["username"] == "student-a" and e["result"] == 403 for e in entries)
    assert client.get("/api/v1/audit-logs", headers=student).status_code == 403


def test_new_api_defaults_to_denied(app, client):
    app.add_url_rule("/api/v1/new-protected", "new_protected", lambda: {"ok": True})
    assert client.get("/api/v1/new-protected").status_code == 401


@pytest.mark.parametrize("kind", ["missing", "invalid", "expired", "revoked"])
def test_sec01_matrix(app, client, login, kind):
    from datetime import UTC, datetime, timedelta

    import jwt

    headers = login("student-a")
    if kind == "missing":
        headers = {}
    elif kind == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif kind == "expired":
        token = headers["Authorization"].split()[1]
        claims = jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=5)
        headers["Authorization"] = "Bearer " + jwt.encode(
            claims, app.config["JWT_SECRET"], algorithm="HS256"
        )
    else:
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    for method, path in [
        ("GET", "/api/v1/me"),
        ("GET", "/api/v1/materials"),
        ("GET", "/api/v1/materials/1"),
        ("POST", "/api/v1/materials"),
        ("GET", "/api/v1/search?q=test"),
        ("POST", "/api/v1/ask"),
        ("POST", "/api/v1/auth/logout"),
        ("GET", "/api/v1/audit-logs"),
        ("GET", "/api/v1/auth/csrf"),
    ]:
        assert client.open(path, method=method, headers=headers).status_code == 401, (kind, path)
    assert client.get("/health").status_code == 200


def test_sec02_both_search_paths(app, client, login, monkeypatch):
    import campusclaw.search as search
    from tests.test_api import upload_material

    teacher = login("teacher-a")
    assert (
        upload_material(client, teacher, "隔离资料", "数据库事务隔离唯一关键词").status_code == 201
    )
    a, b = login("student-a"), login("student-b")
    for fallback in [False, True]:
        if fallback:
            monkeypatch.setattr(search, "search_chunks_by_fts", lambda *_: [])
        assert (
            len(client.get("/api/v1/search?q=事务隔离", headers=a).get_json()["data"]["items"]) == 1
        )
        assert (
            client.get("/api/v1/search?q=事务隔离&class_id=class-a", headers=b).get_json()["data"][
                "items"
            ]
            == []
        )


def test_sec03_no_residual_data(app, client, login):
    from tests.test_api import upload_material

    headers = login("student-a")
    with app.app_context():
        before = [
            db.get_db().execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ["materials", "chunks", "chunks_fts"]
        ]
    assert upload_material(client, headers, "拒绝", "不该落库").status_code == 403
    with app.app_context():
        after = [
            db.get_db().execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ["materials", "chunks", "chunks_fts"]
        ]
    assert before == after == [0, 0, 0]


def test_sec04_direct_session_roles_and_ownership(app, client, login):
    import jwt

    for username, expected in [("student-a", 403), ("teacher-a", 404)]:
        headers = login(username)
        session_id = jwt.decode(
            headers["Authorization"].split()[1], app.config["JWT_SECRET"], algorithms=["HS256"]
        )["jti"]
        with app.app_context():
            actor = db.get_user_by_username(username)
            with pytest.raises(ApiError) as denied:
                db.create_material(
                    class_id="class-b",
                    title="no",
                    filename="x.md",
                    created_by=actor["id"],
                    chunks=[],
                    session_id=session_id,
                )
            assert denied.value.status == expected
            assert db.list_materials("class-b") == []
            assert (
                db.query_operations("class-a", actor["id"], "0000", "9999", 100, 0)[0]["result"]
                == expected
            )


def test_audit_class_filter_and_validation(client, login):
    student = login("student-a")
    assert client.post("/api/v1/materials", headers=student).status_code == 403
    a = login("teacher-a")
    data = client.get("/api/v1/audit-logs", headers=a).get_json()["data"]["items"]
    assert sum(x["result"] == 403 and x["actor"]["username"] == "student-a" for x in data) == 1
    for x in data:
        assert {
            "actor",
            "timestamp",
            "operation",
            "object",
            "result",
            "skill_id",
            "usage_and_duration",
        } <= set(x)
    b = login("teacher-b")
    other = client.get("/api/v1/audit-logs", headers=b).get_json()["data"]["items"]
    assert not any(x["actor"] and x["actor"]["username"] == "student-a" for x in other)
    for query in ["limit=101", "offset=-1", "actor_id=no", "start=bad", "class_id=class-a"]:
        assert client.get("/api/v1/audit-logs?" + query, headers=a).status_code == 400


def test_audit_failure_rolls_back_upload(app, client, login, monkeypatch):
    import io
    import sqlite3

    teacher = login("teacher-a")

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("audit unavailable")

    monkeypatch.setattr(db, "record_operation", unavailable)
    response = client.post(
        "/api/v1/materials",
        headers=teacher,
        data={"file": (io.BytesIO("事务隔离".encode()), "notes.md")},
    )
    assert response.status_code == 503
    with app.app_context():
        assert db.list_materials("class-a") == []
        assert db.get_db().execute("SELECT count(*) FROM chunks_fts").fetchone()[0] == 0


def test_audit_escape_truncate_and_no_secrets(app):
    import json

    with app.app_context():
        actor = db.get_user_by_username("teacher-a")
        db.record_operation("injection-test", actor, "upload", "x\n" * 600, 403)
        row = (
            db.get_db()
            .execute("SELECT payload FROM operation_logs WHERE event_id='injection-test'")
            .fetchone()[0]
        )
        assert "\n" not in row
        assert len(json.loads(row)["object"]) == 512
        assert len(row.encode()) <= 8192


def test_csrf_expiration_wrong_cookie_and_replay(app, client, login):
    teacher = login("teacher-a")
    token = teacher["X-CSRF-Token"]
    with app.app_context():
        import hashlib

        db.get_db().execute(
            "UPDATE csrf_tokens SET expires_at=? WHERE token_hash=?",
            ("2000", hashlib.sha256(token.encode()).hexdigest()),
        )
        db.get_db().commit()
    assert client.post("/api/v1/auth/logout", headers=teacher).status_code == 403
    teacher["X-CSRF-Token"] = client.get("/api/v1/auth/csrf", headers=teacher).get_json()["data"][
        "csrf_token"
    ]
    binding = client.get_cookie("csrf_binding").value
    client.set_cookie("csrf_binding", "wrong")
    assert client.post("/api/v1/auth/logout", headers=teacher).status_code == 403
    client.set_cookie("csrf_binding", binding)
    # consume at a validation failure; even a rejected body consumes a valid token
    assert client.post("/api/v1/ask", headers=teacher, json=[]).status_code == 400
    assert client.post("/api/v1/ask", headers=teacher, json=[]).status_code == 403


def test_csrf_concurrent_consume_once(app, client, login):
    import concurrent.futures

    import jwt

    headers = login("teacher-a")
    session = jwt.decode(
        headers["Authorization"].split()[1], app.config["JWT_SECRET"], algorithms=["HS256"]
    )["jti"]
    binding = client.get_cookie("csrf_binding").value

    def consume():
        with app.app_context():
            return db.consume_csrf(session, binding, headers["X-CSRF-Token"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(lambda _: consume(), range(2)))
    assert sorted(result) == [False, True]


def test_security_backup_restore_and_repeat_migration(app, client, login, tmp_path):
    import sqlite3

    from campusclaw import create_app
    from tests.test_api import upload_material

    teacher = login("teacher-a")
    assert upload_material(client, teacher, "备份资料", "迁移兼容性验证").status_code == 201
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    with app.app_context():
        before = db.get_db().execute("SELECT count(*) FROM operation_logs").fetchone()[0]
        with sqlite3.connect(backup) as target:
            db.get_db().backup(target)
    with sqlite3.connect(backup) as source, sqlite3.connect(restored) as target:
        source.backup(target)
    restored_app = create_app({**app.config, "DATABASE_PATH": str(restored)})
    db.init_db(restored_app)
    with restored_app.app_context():
        assert len(db.list_materials("class-a")) == 1
        assert db.get_db().execute("SELECT count(*) FROM operation_logs").fetchone()[0] == before
        assert db.get_db().execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 2


def test_parallel_initial_migration_is_safe(app, tmp_path):
    import concurrent.futures

    from campusclaw import create_app

    target = str(tmp_path / "parallel.sqlite3")

    def initialize(_):
        instance = create_app({**app.config, "DATABASE_PATH": target})
        with instance.app_context():
            return db.get_db().execute("SELECT count(*) FROM schema_migrations").fetchone()[0]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(initialize, range(2))) == [2, 2]
