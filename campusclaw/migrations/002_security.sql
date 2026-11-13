-- version: 002_security
-- rollback: DROP TABLE csrf_tokens; DROP TABLE operation_logs;
CREATE TABLE csrf_tokens (
 token_hash TEXT PRIMARY KEY, jti TEXT NOT NULL REFERENCES auth_sessions(jti),
 binding_hash TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE operation_logs (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
 class_id TEXT NOT NULL, actor_id INTEGER, created_at TEXT NOT NULL,
 payload TEXT NOT NULL CHECK(json_valid(payload))
);
CREATE INDEX idx_audit_class_time ON operation_logs(class_id, created_at, id);
CREATE INDEX idx_audit_actor_time ON operation_logs(actor_id, created_at);
