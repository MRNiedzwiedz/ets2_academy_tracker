CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name))>0), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS profiles (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), ets_profile_id TEXT NOT NULL,
 source_path TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenarios (
 id INTEGER PRIMARY KEY, scenario_code TEXT UNIQUE NOT NULL, book_code TEXT, display_name TEXT
);
CREATE TABLE IF NOT EXISTS import_snapshots (
 id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), file_sha256 TEXT NOT NULL,
 source_path TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 import_status TEXT NOT NULL, event_count INTEGER NOT NULL DEFAULT 0, error_message TEXT, warnings_json TEXT NOT NULL DEFAULT '[]',
 UNIQUE(profile_id,file_sha256)
);
CREATE TABLE IF NOT EXISTS academy_events (
 id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), event_type TEXT NOT NULL,
 event_timestamp INTEGER NOT NULL, object_id TEXT, link_raw TEXT, event_identity TEXT NOT NULL,
 signature TEXT NOT NULL, raw_fields_json TEXT NOT NULL, result_json TEXT,
 UNIQUE(profile_id,event_identity)
);
CREATE TABLE IF NOT EXISTS snapshot_events (
 snapshot_id INTEGER NOT NULL REFERENCES import_snapshots(id), position INTEGER NOT NULL,
 event_id INTEGER NOT NULL REFERENCES academy_events(id), PRIMARY KEY(snapshot_id,position)
);
CREATE TABLE IF NOT EXISTS attempts (
 id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
 attempt_number INTEGER NOT NULL, start_timestamp INTEGER, end_timestamp INTEGER, score REAL, rank_raw TEXT,
 game_duration_raw TEXT, elapsed_seconds INTEGER, result_object_id TEXT,
 status TEXT NOT NULL CHECK(status IN ('completed','failed','interrupted','in_progress','unknown')),
 match_confidence TEXT NOT NULL, logical_identity TEXT NOT NULL,
 start_identity TEXT, end_identity TEXT, source_snapshot_id INTEGER NOT NULL REFERENCES import_snapshots(id),
 UNIQUE(profile_id,logical_identity), UNIQUE(profile_id,scenario_id,attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON academy_events(profile_id,event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_signature ON academy_events(profile_id,signature);
CREATE INDEX IF NOT EXISTS idx_attempt_scenario ON attempts(scenario_id);
CREATE INDEX IF NOT EXISTS idx_attempt_time ON attempts(profile_id,start_timestamp,end_timestamp);
CREATE INDEX IF NOT EXISTS idx_attempt_end ON attempts(profile_id,end_identity);
CREATE TABLE IF NOT EXISTS attempt_reconciliations (
 id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), retired_attempt_json TEXT NOT NULL,
 surviving_attempt_id INTEGER NOT NULL REFERENCES attempts(id), snapshot_id INTEGER NOT NULL REFERENCES import_snapshots(id)
);
PRAGMA user_version=2;
