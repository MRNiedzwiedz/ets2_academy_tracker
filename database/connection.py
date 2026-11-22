from contextlib import contextmanager
from pathlib import Path
import sqlite3
from database.migrations import migrate


@contextmanager
def connect(path: str | Path):
    db = sqlite3.connect(str(path), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    try:
        yield db
    finally:
        db.close()


def initialize(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        migrate(db)
