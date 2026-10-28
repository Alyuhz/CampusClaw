from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g
from werkzeug.security import generate_password_hash

MIGRATIONS_DIR = Path(__file__).with_name("migrations")

SEED_USERS = (
    ("teacher-a", "teacher", "class-a"),
    ("student-a", "student", "class-a"),
    ("teacher-b", "teacher", "class-b"),
    ("student-b", "student", "class-b"),
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database = Path(current_app.config["DATABASE_PATH"])
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def _seed_users(connection: sqlite3.Connection, app: Flask) -> None:
    passwords = {
        "teacher": app.config["SEED_TEACHER_PASSWORD"],
        "student": app.config["SEED_STUDENT_PASSWORD"],
    }
    hashes: dict[str, str] = {}
    for username, role, class_id in SEED_USERS:
        if role not in hashes:
            hashes[role] = generate_password_hash(passwords[role])
        connection.execute(
            """
            INSERT INTO users(username, password_hash, role, class_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO NOTHING
            """,
            (username, hashes[role], role, class_id, utc_now()),
        )


def _apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration.name in applied:
            continue
        statement = migration.read_text(encoding="utf-8")
        version = migration.name.replace("'", "''")
        connection.executescript(
            "BEGIN;\n"
            f"{statement}\n"
            "INSERT INTO schema_migrations(version, applied_at) "
            f"VALUES ('{version}', '{utc_now()}');\n"
            "COMMIT;"
        )


def init_db(app: Flask) -> None:
    with app.app_context():
        connection = get_db()
        _apply_migrations(connection)
        _seed_users(connection, app)
        connection.commit()


def database_is_ready() -> bool:
    try:
        return get_db().execute("SELECT 1").fetchone()[0] == 1
    except sqlite3.Error:
        return False


def get_user_by_username(username: str) -> sqlite3.Row | None:
    return (
        get_db()
        .execute(
            "SELECT id, username, password_hash, role, class_id FROM users WHERE username = ?",
            (username,),
        )
        .fetchone()
    )


def create_session(*, jti: str, user_id: int, expires_at: str, created_at: str) -> None:
    connection = get_db()
    connection.execute(
        """
        INSERT INTO auth_sessions(jti, user_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (jti, user_id, expires_at, created_at),
    )
    connection.commit()


def get_active_session(jti: str) -> sqlite3.Row | None:
    return (
        get_db()
        .execute(
            """
        SELECT s.jti, s.expires_at, u.id, u.username, u.role, u.class_id
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.jti = ? AND s.revoked_at IS NULL AND s.expires_at > ?
        """,
            (jti, utc_now()),
        )
        .fetchone()
    )


def revoke_session(jti: str) -> None:
    connection = get_db()
    connection.execute(
        "UPDATE auth_sessions SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL",
        (utc_now(), jti),
    )
    connection.commit()


def list_materials(class_id: str) -> list[sqlite3.Row]:
    return list(
        get_db()
        .execute(
            """
            SELECT id, title, filename, created_at
            FROM materials
            WHERE class_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (class_id,),
        )
        .fetchall()
    )


def create_material(
    *,
    class_id: str,
    title: str,
    filename: str,
    created_by: int,
    chunks: list[dict[str, Any]],
) -> int:
    connection = get_db()
    created_at = utc_now()
    try:
        cursor = connection.execute(
            """
            INSERT INTO materials(class_id, title, filename, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (class_id, title, filename, created_by, created_at),
        )
        material_id = int(cursor.lastrowid)
        for chunk in chunks:
            cursor = connection.execute(
                """
                INSERT INTO chunks(
                    material_id, class_id, chunk_index, content, start_line, end_line
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    material_id,
                    class_id,
                    chunk["chunk_index"],
                    chunk["content"],
                    chunk["start_line"],
                    chunk["end_line"],
                ),
            )
            connection.execute(
                "INSERT INTO chunks_fts(rowid, content) VALUES (?, ?)",
                (cursor.lastrowid, chunk["content"]),
            )
        connection.commit()
        return material_id
    except Exception:
        connection.rollback()
        raise


def get_material_for_class(material_id: int, class_id: str) -> sqlite3.Row | None:
    row = (
        get_db()
        .execute(
            """
        SELECT id, class_id, title, filename, created_at
        FROM materials
        WHERE id = ?
        """,
            (material_id,),
        )
        .fetchone()
    )
    if row is None or row["class_id"] != class_id:
        return None
    return row


def list_chunks(material_id: int, class_id: str) -> list[sqlite3.Row]:
    return list(
        get_db()
        .execute(
            """
            SELECT id, chunk_index, content, start_line, end_line
            FROM chunks
            WHERE material_id = ? AND class_id = ?
            ORDER BY chunk_index
            """,
            (material_id, class_id),
        )
        .fetchall()
    )


def search_chunks_by_fts(class_id: str, fts_query: str, limit: int) -> list[sqlite3.Row]:
    try:
        return list(
            get_db()
            .execute(
                """
                SELECT
                    c.id, c.material_id, c.chunk_index, c.content, c.start_line, c.end_line,
                    m.title, bm25(chunks_fts) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                JOIN materials m ON m.id = c.material_id
                WHERE chunks_fts MATCH ? AND c.class_id = ?
                ORDER BY rank, c.id
                LIMIT ?
                """,
                (fts_query, class_id, limit),
            )
            .fetchall()
        )
    except sqlite3.OperationalError:
        return []


def search_chunks_by_like(class_id: str, terms: list[str], limit: int) -> list[sqlite3.Row]:
    escaped = [term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for term in terms]
    predicates = " OR ".join("c.content LIKE ? ESCAPE '\\'" for _ in escaped)
    return list(
        get_db()
        .execute(
            f"""
            SELECT
                c.id, c.material_id, c.chunk_index, c.content, c.start_line, c.end_line,
                m.title, 0.0 AS rank
            FROM chunks c
            JOIN materials m ON m.id = c.material_id
            WHERE c.class_id = ? AND ({predicates})
            ORDER BY c.id
            LIMIT ?
            """,
            (class_id, *(f"%{term}%" for term in escaped), limit),
        )
        .fetchall()
    )
