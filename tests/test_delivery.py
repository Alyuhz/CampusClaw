from __future__ import annotations

import concurrent.futures
import json

import pytest

from campusclaw import create_app, db
from campusclaw.search import search
from campusclaw.search_cache import SearchCache
from tests.test_api import upload_material


def test_ready_readonly_and_database_failure(app, client, monkeypatch):
    with app.app_context():
        before = db.get_db().total_changes
        assert db.ready_for_traffic()
        assert db.get_db().total_changes == before
    assert client.get("/ready").status_code == 200
    monkeypatch.setattr("campusclaw.app.ready_for_traffic", lambda: False)
    assert client.get("/ready").status_code == 503
    monkeypatch.undo()
    assert client.get("/ready").status_code == 200


def test_ready_rejects_missing_migration(app):
    with app.app_context():
        db.get_db().execute("DELETE FROM schema_migrations WHERE version='003_delivery.sql'")
        db.get_db().commit()
        assert not db.ready_for_traffic()


def test_cache_class_write_invalidation_and_revocation(app, client, login):
    app.config["SEARCH_CACHE_ENABLED"] = True
    teacher = login("teacher-a")
    assert upload_material(client, teacher, "one", "事务隔离知识").status_code == 201
    a, b = login("student-a"), login("student-b")
    assert len(client.get("/api/v1/search?q=事务隔离", headers=a).get_json()["data"]["items"]) == 1
    assert client.get("/api/v1/search?q=事务隔离", headers=b).get_json()["data"]["items"] == []
    with app.app_context():
        assert db.class_revision("class-a") == 1
        copy = search("class-a", "事务隔离", 8)
        copy.clear()
        assert len(search("class-a", "事务隔离", 8)) == 1
    second = create_app(dict(app.config))
    other = second.test_client()
    response = other.post(
        "/api/v1/auth/login", json={"username": "teacher-a", "password": "teacher-pass"}
    )
    data = response.get_json()["data"]
    headers = {"Authorization": "Bearer " + data["token"], "X-CSRF-Token": data["csrf_token"]}
    assert upload_material(other, headers, "two", "事务隔离新增").status_code == 201
    assert len(client.get("/api/v1/search?q=事务隔离", headers=a).get_json()["data"]["items"]) == 2
    a["X-CSRF-Token"] = client.get("/api/v1/auth/csrf", headers=a).get_json()["data"]["csrf_token"]
    assert client.post("/api/v1/auth/logout", headers=a).status_code == 200
    assert client.get("/api/v1/search?q=事务隔离", headers=a).status_code == 401


def test_cache_bound_ttl_and_copy():
    cache = SearchCache(limit=2)
    cache.put(("a",), [{"n": 1}])
    cache.put(("b",), [{"n": 2}])
    cache.get(("a",))[0]["n"] = 9
    assert cache.get(("a",)) == [{"n": 1}]
    cache.put(("c",), [])
    assert len(cache.entries) == 2 and cache.get(("b",)) is None
    immediate = SearchCache(ttl=0)
    immediate.put(("a",), [1])
    assert immediate.get(("a",)) is None


def test_revision_rolls_back_with_audit(app, client, login, monkeypatch):
    import io

    teacher = login("teacher-a")

    def fail(*args, **kwargs):
        raise RuntimeError("audit fault")

    monkeypatch.setattr(db, "record_operation", fail)
    assert (
        client.post(
            "/api/v1/materials", headers=teacher, data={"file": (io.BytesIO(b"content"), "x.md")}
        ).status_code
        == 503
    )
    with app.app_context():
        assert db.class_revision("class-a") == 0
        assert db.list_materials("class-a") == []


def test_metrics_protected_and_persistent(app, client, login):
    app.config.update(
        TELEMETRY_ENABLED=True, METRICS_TOKEN="metrics-test-token-with-at-least-32-bytes"
    )
    assert client.get("/internal/metrics").status_code == 401
    student = login("student-a")
    assert client.get("/internal/metrics", headers=student).status_code == 401
    assert client.get("/api/v1/search?q=词条", headers=student).status_code == 200
    headers = {"Authorization": "Bearer " + app.config["METRICS_TOKEN"]}
    text = client.get("/internal/metrics", headers=headers).get_data(as_text=True)
    assert 'capability_requests_total{capability="knowledge-search",status="200"} 1' in text
    assert "student-a" not in text and "class-a" not in text
    restored = create_app(dict(app.config))
    assert (
        restored.test_client().get("/internal/metrics", headers=headers).get_data(as_text=True)
        == text
    )
    with app.app_context():
        totals, active = db.metric_snapshot()
        assert totals[0]["n"] == 1 and active == {}


def test_metrics_concurrent_exact_and_duplicate(app):
    app.config["TELEMETRY_ENABLED"] = True

    def finish(i):
        with app.app_context():
            actor = db.get_user_by_username("teacher-a")
            db.finish_operation(f"parallel-{i}", actor, "search.find", 200, 12)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(finish, range(30)))
    finish(0)
    with app.app_context():
        rows, _ = db.metric_snapshot()
        assert rows[0]["n"] == 30
        buckets = json.loads(rows[0]["buckets"])
        assert buckets[0] == 0 and buckets[-1] == 30
        assert rows[0]["sum_seconds"] == pytest.approx(0.36)


def test_lease_renew_complete_expire(app):
    with app.app_context():
        db.begin_lease("active", "knowledge-search")
        assert db.metric_snapshot()[1] == {"knowledge-search": 1}
        db.get_db().execute("UPDATE request_leases SET expires=0")
        db.get_db().commit()
        assert db.metric_snapshot()[1] == {}
        db.renew_leases(["active"])
        assert db.metric_snapshot()[1] == {"knowledge-search": 1}
        app.config["TELEMETRY_ENABLED"] = True
        db.finish_operation("active", None, "search.find", 401, 1)
        assert db.metric_snapshot()[1] == {}


def test_metrics_storage_failure_is_not_zero(app, client, monkeypatch):
    app.config.update(
        TELEMETRY_ENABLED=True, METRICS_TOKEN="metrics-test-token-with-at-least-32-bytes"
    )

    def fail():
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(db, "metric_snapshot", fail)
    assert (
        client.get(
            "/internal/metrics", headers={"Authorization": "Bearer " + app.config["METRICS_TOKEN"]}
        ).status_code
        == 503
    )


def test_metric_nonascii_invalid_token_rejected(app, client):
    app.config.update(
        TELEMETRY_ENABLED=True, METRICS_TOKEN="metrics-test-token-with-at-least-32-bytes"
    )
    assert client.get("/internal/metrics", headers={"Authorization": "Bearer é"}).status_code == 401


@pytest.mark.parametrize(
    "table", ["auth_sessions", "csrf_tokens", "chunks_fts", "metric_receipts", "request_leases"]
)
def test_ready_rejects_missing_required_table(app, table):
    with app.app_context():
        connection = db.get_db()
        connection.execute(f"DROP TABLE {table}")
        connection.commit()
        assert not db.ready_for_traffic()
