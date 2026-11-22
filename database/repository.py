from pathlib import Path
from database.connection import connect, initialize


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        initialize(self.path)

    def query(self, sql: str, params=()) -> list[dict]:
        with connect(self.path) as db:
            return [dict(row) for row in db.execute(sql, params)]

    def execute(self, sql: str, params=()) -> int:
        with connect(self.path) as db, db:
            return db.execute(sql, params).lastrowid

    def add_user(self, name: str) -> int:
        if not name.strip():
            raise ValueError("Podaj nazwę użytkownika")
        return self.execute("INSERT INTO users(name) VALUES(?)", (name.strip(),))

    def add_profile(self, user_id: int, name: str, path: str) -> int:
        source = Path(path).expanduser().resolve()
        if source.is_dir():
            source /= "academy_book_states.sii"
        if not name.strip():
            raise ValueError("Podaj nazwę profilu")
        return self.execute("INSERT INTO profiles(user_id,ets_profile_id,source_path) VALUES(?,?,?)",
                            (user_id, name.strip(), str(source)))

    def profiles(self, enabled=False):
        return self.query("SELECT p.*,u.name user_name FROM profiles p JOIN users u ON u.id=p.user_id" +
                          (" WHERE p.enabled=1" if enabled else "") + " ORDER BY p.id")

    def attempts(self, user_id=None, profile_id=None, scenario=None, status=None, date_from=None, date_to=None):
        sql = """SELECT a.*,u.name user_name,p.ets_profile_id profile_name,s.scenario_code,s.display_name,
                 EXISTS(SELECT 1 FROM snapshot_events se JOIN academy_events e ON e.id=se.event_id
                    WHERE se.snapshot_id=(SELECT id FROM import_snapshots WHERE profile_id=a.profile_id
                      AND import_status='processed' ORDER BY id DESC LIMIT 1)
                    AND e.event_identity IN (a.start_identity,a.end_identity)) visible_in_latest
                 FROM attempts a JOIN profiles p ON p.id=a.profile_id
                 JOIN users u ON u.id=p.user_id JOIN scenarios s ON s.id=a.scenario_id WHERE 1=1"""
        params = []
        for clause, value in [("u.id=?", user_id), ("p.id=?", profile_id), ("s.scenario_code=?", scenario),
                              ("a.status=?", status), ("COALESCE(a.start_timestamp,a.end_timestamp)>=?", date_from),
                              ("COALESCE(a.start_timestamp,a.end_timestamp)<=?", date_to)]:
            if value is not None and value != "":
                sql += " AND " + clause
                params.append(value)
        return self.query(sql + " ORDER BY COALESCE(a.start_timestamp,a.end_timestamp),a.id", params)
