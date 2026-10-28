-- version: 001_initial
-- rollback: drop all tables and indexes created by this migration

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
    class_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE auth_sessions (
    jti TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id TEXT NOT NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    class_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    UNIQUE (material_id, chunk_index)
);

CREATE INDEX idx_materials_class ON materials(class_id);
CREATE INDEX idx_chunks_class ON chunks(class_id);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,
    tokenize = 'trigram'
);
