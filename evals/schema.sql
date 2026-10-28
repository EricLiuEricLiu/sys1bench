-- Proposed Cloudflare D1 / SQLite schema. No infrastructure is provisioned.
-- These are trusted server tables. Never expose attempts, labels, or record_json
-- through a public API. Human answers must be scored on the server before import.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    benchmark_id TEXT NOT NULL,
    benchmark_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    stimuli_sha256 TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    protocol_sha256 TEXT NOT NULL,
    config_sha256 TEXT NOT NULL,
    plan_sha256 TEXT NOT NULL,
    participant_kind TEXT NOT NULL CHECK (participant_kind IN ('human','model','mock')),
    is_mock INTEGER NOT NULL CHECK (is_mock IN (0,1)),
    provider TEXT,
    model_requested TEXT,
    assignment_seed TEXT NOT NULL,
    variant TEXT NOT NULL CHECK (variant IN ('primary','mirrored')),
    split_status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    complete INTEGER NOT NULL CHECK (complete IN (0,1)),
    planned_scored INTEGER NOT NULL CHECK (planned_scored > 0),
    record_json TEXT NOT NULL CHECK (json_valid(record_json)),
    CHECK ((participant_kind = 'mock') = (is_mock = 1))
);

CREATE TABLE IF NOT EXISTS eval_answers (
    run_id TEXT NOT NULL REFERENCES eval_runs(run_id),
    item_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('practice','scored')),
    A_post_id TEXT NOT NULL,
    B_post_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('valid','invalid','timeout','error','refused','provider_incomplete','unexpected_output','not_run')),
    choice TEXT CHECK (choice IN ('A','B') OR choice IS NULL),
    correct_choice TEXT NOT NULL CHECK (correct_choice IN ('A','B')),
    correct INTEGER NOT NULL CHECK (correct IN (0,1)),
    primary_latency_ms REAL,
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    record_json TEXT NOT NULL CHECK (json_valid(record_json)),
    PRIMARY KEY (run_id, item_id),
    UNIQUE (run_id, ordinal),
    CHECK ((status = 'valid' AND choice IS NOT NULL) OR (status != 'valid' AND choice IS NULL)),
    CHECK (correct = CASE WHEN choice = correct_choice THEN 1 ELSE 0 END)
);

CREATE TABLE IF NOT EXISTS eval_attempts (
    run_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    status TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    request_id TEXT,
    model_returned TEXT,
    latency_ms REAL NOT NULL,
    record_json TEXT NOT NULL CHECK (json_valid(record_json)),
    PRIMARY KEY (run_id, item_id, attempt),
    FOREIGN KEY (run_id, item_id) REFERENCES eval_answers(run_id, item_id)
);

CREATE INDEX IF NOT EXISTS eval_cohort ON eval_runs
    (benchmark_id, benchmark_version, dataset_version, stimuli_sha256, protocol_sha256, config_sha256, participant_kind, variant);

-- Per-run aggregates retain protocol and dataset boundaries. This view deliberately
-- excludes mock fixtures and incomplete runs. It makes no population-rank claim.
-- Publishing a leaderboard still requires a server API, review, and deployment.
CREATE VIEW IF NOT EXISTS eval_public_run_aggregates AS
SELECT r.run_id, r.benchmark_id, r.benchmark_version, r.dataset_version,
       r.stimuli_sha256, r.protocol_version, r.protocol_sha256, r.config_sha256,
       r.participant_kind, r.provider, r.model_requested, r.variant, r.split_status,
       r.started_at, r.finished_at, COUNT(*) AS denominator,
       SUM(a.correct) AS correct, 1.0 * SUM(a.correct) / COUNT(*) AS accuracy,
       SUM(CASE WHEN a.status != 'valid' THEN 1 ELSE 0 END) AS failed_or_invalid
FROM eval_runs r JOIN eval_answers a ON a.run_id = r.run_id
WHERE r.is_mock = 0 AND r.participant_kind IN ('human','model')
  AND r.complete = 1 AND a.kind = 'scored'
GROUP BY r.run_id
HAVING COUNT(*) = r.planned_scored;
