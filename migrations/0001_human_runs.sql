CREATE TABLE IF NOT EXISTS human_runs (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL,
  cohort TEXT NOT NULL,
  dataset_version TEXT NOT NULL,
  assignments TEXT NOT NULL CHECK (json_valid(assignments)),
  next_ordinal INTEGER NOT NULL DEFAULT 0,
  opened_at INTEGER,
  created_at INTEGER NOT NULL,
  finished_at INTEGER,
  is_test INTEGER NOT NULL DEFAULT 0 CHECK (is_test IN (0,1)),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','complete','aborted'))
);
CREATE TABLE IF NOT EXISTS human_answers (
  run_id TEXT NOT NULL REFERENCES human_runs(id),
  ordinal INTEGER NOT NULL,
  pair_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('practice','scored')),
  choice TEXT CHECK (choice IN ('left','right') OR choice IS NULL),
  correct INTEGER NOT NULL CHECK (correct IN (0,1)),
  response_ms REAL,
  observed_ms REAL NOT NULL,
  answered_at INTEGER NOT NULL,
  PRIMARY KEY (run_id, ordinal)
);
CREATE TABLE IF NOT EXISTS human_first_results (
  participant_id TEXT NOT NULL,
  cohort TEXT NOT NULL,
  run_id TEXT NOT NULL UNIQUE REFERENCES human_runs(id),
  correct INTEGER NOT NULL CHECK (correct BETWEEN 0 AND 15),
  total INTEGER NOT NULL CHECK (total=15),
  completed_at INTEGER NOT NULL,
  PRIMARY KEY (participant_id, cohort)
);
CREATE INDEX IF NOT EXISTS human_results_cohort ON human_first_results(cohort, correct);
CREATE INDEX IF NOT EXISTS human_runs_participant ON human_runs(participant_id, created_at);
