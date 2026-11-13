-- version: 003_delivery
-- phase: expand + migrate; no old columns removed
-- rollback: retain new tables for app rollback; destructive schema rollback requires backup
CREATE TABLE class_revisions (class_id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
CREATE TABLE metric_totals (
 capability TEXT NOT NULL, status INTEGER NOT NULL, n INTEGER NOT NULL,
 sum_seconds REAL NOT NULL, buckets TEXT NOT NULL CHECK(json_valid(buckets)),
 PRIMARY KEY(capability,status)
);
CREATE TABLE metric_receipts (event_id TEXT PRIMARY KEY REFERENCES operation_logs(event_id));
CREATE TABLE request_leases (event_id TEXT PRIMARY KEY, capability TEXT NOT NULL, expires REAL NOT NULL);
CREATE INDEX idx_request_lease_expiry ON request_leases(expires);
