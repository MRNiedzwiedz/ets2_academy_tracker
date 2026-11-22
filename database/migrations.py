from pathlib import Path
import sqlite3


def migrate(db: sqlite3.Connection) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > 2:
        raise RuntimeError("Baza pochodzi z nowszej wersji aplikacji")
    if version == 0:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        db.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
    elif version == 1:
        db.executescript("""BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS attempt_reconciliations (
              id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), retired_attempt_json TEXT NOT NULL,
              surviving_attempt_id INTEGER NOT NULL REFERENCES attempts(id), snapshot_id INTEGER NOT NULL REFERENCES import_snapshots(id));
            PRAGMA user_version=2;
            COMMIT;""")
