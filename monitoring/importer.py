from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import heapq
import json
import logging
from pathlib import Path

from academy.academy_parser import academy_events
from academy.decoder import Decoder
from academy.event_matcher import match_attempts
from academy.exceptions import ParseError
from academy.models import Event
from academy.sii_parser import parse_sii
from database.connection import connect
from database.repository import Repository
from monitoring.snapshot import Snapshot, stable_snapshot

log = logging.getLogger(__name__)


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if isinstance(value, str) and value.startswith("_nameless."):
        return "<local-reference>"
    return value


def event_signature(event: Event) -> str:
    # Resolve result content, exclude volatile allocator addresses, retain all raw goals.
    content = [event.event_type, event.timestamp, canonical(event.fields), canonical(event.result)]
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ordered_history(db, profile_id: int) -> list[Event]:
    """Merge observed log-order constraints without sorting by wall-clock time.

    Late import of an older, overlapping snapshot can insert a missing start
    before an already-observed end. Independent disconnected segments retain
    first-observed order; conflicting orders are rejected rather than guessed.
    """
    records = {r["id"]: r for r in db.execute("SELECT * FROM academy_events WHERE profile_id=? ORDER BY id",(profile_id,))}
    edges = {eid:set() for eid in records}
    incoming = {eid:0 for eid in records}
    previous = None
    for row in db.execute("""SELECT se.* FROM snapshot_events se JOIN import_snapshots s ON s.id=se.snapshot_id
                           WHERE s.profile_id=? AND s.import_status IN ('processed','processing') ORDER BY se.snapshot_id,se.position""",(profile_id,)):
        if previous is not None and previous["snapshot_id"] == row["snapshot_id"]:
            src,dst = previous["event_id"],row["event_id"]
            if dst not in edges[src]:
                edges[src].add(dst)
                incoming[dst] += 1
        previous = row
    ready = [eid for eid,count in incoming.items() if count == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        eid = heapq.heappop(ready)
        r = records[eid]
        ordered.append(Event(r["event_type"],r["event_timestamp"],r["object_id"],r["link_raw"],
                             json.loads(r["raw_fields_json"]),json.loads(r["result_json"]),r["event_identity"]))
        for dst in edges[eid]:
            incoming[dst] -= 1
            if not incoming[dst]:
                heapq.heappush(ready,dst)
    if len(ordered) != len(records):
        raise ParseError("Sprzeczna kolejność zdarzeń między zapisami; import wycofany")
    return ordered


@dataclass(frozen=True)
class ImportResult:
    snapshot_id: int
    events: int
    new_attempts: int
    duplicate: bool = False
    warnings: tuple[str, ...] = ()


class Importer:
    def __init__(self, repository: Repository, decoder: Decoder | None = None):
        self.repository = repository
        self.decoder = decoder or Decoder()

    def import_file(self, profile_id: int, stop=None) -> ImportResult:
        profile = self.repository.query("SELECT * FROM profiles WHERE id=?", (profile_id,))
        if not profile:
            raise ValueError("Nieznany profil")
        path = Path(profile[0]["source_path"])
        return self.import_snapshot(profile_id, stable_snapshot(path, stop=stop), str(path))

    def import_snapshot(self, profile_id: int, snapshot: Snapshot, source_path: str = "") -> ImportResult:
        existing = self.repository.query("SELECT * FROM import_snapshots WHERE profile_id=? AND file_sha256=? AND import_status='processed'",
                                         (profile_id, snapshot.sha256))
        if existing:
            row = existing[0]
            return ImportResult(row["id"], row["event_count"], 0, True, tuple(json.loads(row["warnings_json"])))
        try:
            decoded = self.decoder.decode(snapshot.raw)
            events = academy_events(parse_sii(decoded.text))
            log.info("Academy events parsed: %d", len(events))
            with connect(self.repository.path) as db, db:
                db.execute("BEGIN IMMEDIATE")
                # Recheck inside write transaction: concurrent import cannot duplicate work.
                old = db.execute("SELECT * FROM import_snapshots WHERE profile_id=? AND file_sha256=?", (profile_id, snapshot.sha256)).fetchone()
                if old and old["import_status"] == "processed":
                    return ImportResult(old["id"], old["event_count"], 0, True)
                db.execute("""INSERT INTO import_snapshots(profile_id,file_sha256,source_path,import_status)
                              VALUES(?,?,?,'processing') ON CONFLICT(profile_id,file_sha256) DO UPDATE SET
                              import_status='processing',error_message=NULL,imported_at=CURRENT_TIMESTAMP""",
                           (profile_id, snapshot.sha256, source_path))
                sid = db.execute("SELECT id FROM import_snapshots WHERE profile_id=? AND file_sha256=?", (profile_id, snapshot.sha256)).fetchone()[0]
                occurrences = Counter()
                for position, event in enumerate(events):
                    signature = event_signature(event)
                    occurrences[signature] += 1
                    event.identity = f"{signature}:{occurrences[signature]}"
                    known = db.execute("SELECT event_identity FROM academy_events WHERE profile_id=? AND signature=? ORDER BY id LIMIT 1 OFFSET ?",
                                       (profile_id,signature,occurrences[signature]-1)).fetchone()
                    if known:
                        event.identity = known[0]
                    if event.event_type == "scenario_end" and event.result:
                        # A previously dangling result reference can resolve later.
                        # Reuse only an unambiguous unresolved event envelope.
                        unresolved = [r for r in db.execute("""SELECT * FROM academy_events
                            WHERE profile_id=? AND event_type='scenario_end' AND event_timestamp=? AND result_json='null'""",
                            (profile_id,event.timestamp))
                            if canonical(json.loads(r["raw_fields_json"])) == canonical(event.fields)]
                        current_same_envelope = sum(e.event_type == event.event_type and e.timestamp == event.timestamp
                                                    and canonical(e.fields) == canonical(event.fields) for e in events)
                        if len(unresolved) == 1 and current_same_envelope == 1:
                            event.identity = unresolved[0]["event_identity"]
                    db.execute("""INSERT INTO academy_events(profile_id,event_type,event_timestamp,object_id,link_raw,event_identity,signature,raw_fields_json,result_json)
                                  VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_id,event_identity) DO UPDATE SET
                                  object_id=excluded.object_id,link_raw=excluded.link_raw,signature=excluded.signature,
                                  raw_fields_json=excluded.raw_fields_json,result_json=excluded.result_json""",
                               (profile_id,event.event_type,event.timestamp,event.object_id,event.link,event.identity,signature,
                                json.dumps(event.fields),json.dumps(event.result)))
                    eid = db.execute("SELECT id FROM academy_events WHERE profile_id=? AND event_identity=?", (profile_id,event.identity)).fetchone()[0]
                    db.execute("INSERT INTO snapshot_events VALUES(?,?,?)", (sid,position,eid))
                history = ordered_history(db,profile_id)
                before = db.execute("SELECT count(*) FROM attempts WHERE profile_id=?",(profile_id,)).fetchone()[0]
                for attempt in match_attempts(history):
                    code = attempt.scenario_code
                    parts = code.split(".")
                    book = parts[2] if len(parts)>2 else None
                    db.execute("INSERT INTO scenarios(scenario_code,book_code) VALUES(?,?) ON CONFLICT(scenario_code) DO NOTHING",(code,book))
                    scenario_id = db.execute("SELECT id FROM scenarios WHERE scenario_code=?",(code,)).fetchone()[0]
                    if attempt.start_identity and attempt.end_identity:
                        # The same resolved end can replace an earlier unknown orphan
                        # when a separate start record already exists.
                        orphan = db.execute("SELECT * FROM attempts WHERE profile_id=? AND end_identity=? AND start_identity IS NULL",
                                            (profile_id,attempt.end_identity)).fetchone()
                        started = db.execute("SELECT id FROM attempts WHERE profile_id=? AND logical_identity=?",
                                             (profile_id,attempt.logical_identity)).fetchone()
                        if orphan and started:
                            # Retain provenance of this reconciliation without treating
                            # an observation of the same attempt as an extra attempt.
                            db.execute("INSERT INTO attempt_reconciliations(profile_id,retired_attempt_json,surviving_attempt_id,snapshot_id) VALUES(?,?,?,?)",
                                       (profile_id,json.dumps(dict(orphan)),started[0],sid))
                            db.execute("DELETE FROM attempts WHERE id=?",(orphan["id"],))
                    if attempt.start_identity and attempt.end_identity:
                        # Enrich an orphan end seen in an earlier truncated snapshot.
                        db.execute("""UPDATE attempts SET logical_identity=?,start_identity=?,start_timestamp=?
                                      WHERE profile_id=? AND end_identity=? AND start_identity IS NULL
                                      AND NOT EXISTS(SELECT 1 FROM attempts WHERE profile_id=? AND logical_identity=?)""",
                                   (attempt.logical_identity,attempt.start_identity,attempt.start_timestamp,
                                    profile_id,attempt.end_identity,profile_id,attempt.logical_identity))
                    number = db.execute("SELECT COALESCE(MAX(attempt_number),0)+1 FROM attempts WHERE profile_id=? AND scenario_id=?",(profile_id,scenario_id)).fetchone()[0]
                    previous_attempt = db.execute("SELECT scenario_id,attempt_number FROM attempts WHERE profile_id=? AND logical_identity=?",
                                                  (profile_id,attempt.logical_identity)).fetchone()
                    if previous_attempt and previous_attempt["scenario_id"] == scenario_id:
                        number = previous_attempt["attempt_number"]
                    db.execute("""INSERT INTO attempts(profile_id,scenario_id,attempt_number,start_timestamp,end_timestamp,score,rank_raw,
                                  game_duration_raw,elapsed_seconds,result_object_id,status,match_confidence,logical_identity,
                                  start_identity,end_identity,source_snapshot_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                                  ON CONFLICT(profile_id,logical_identity) DO UPDATE SET
                                  end_timestamp=excluded.end_timestamp,score=excluded.score,rank_raw=excluded.rank_raw,
                                  scenario_id=excluded.scenario_id,
                                  attempt_number=excluded.attempt_number,
                                  game_duration_raw=excluded.game_duration_raw,elapsed_seconds=excluded.elapsed_seconds,
                                  result_object_id=excluded.result_object_id,status=excluded.status,match_confidence=excluded.match_confidence,
                                  end_identity=excluded.end_identity""",
                               (profile_id,scenario_id,number,attempt.start_timestamp,attempt.end_timestamp,attempt.score,
                                attempt.rank_raw,attempt.game_duration_raw,attempt.elapsed_seconds,attempt.result_object_id,
                                attempt.status,attempt.match_confidence,attempt.logical_identity,attempt.start_identity,attempt.end_identity,sid))
                after = db.execute("SELECT count(*) FROM attempts WHERE profile_id=?",(profile_id,)).fetchone()[0]
                warnings = list(decoded.warnings)
                if any(count > 1 for count in occurrences.values()):
                    warnings.append("Identyczne zdarzenia rozróżniono kolejnością wystąpień; przy obciętym dzienniku tożsamość może być niejednoznaczna")
                db.execute("UPDATE import_snapshots SET import_status='processed',event_count=?,warnings_json=? WHERE id=?",
                           (len(events),json.dumps(warnings),sid))
            log.info("New attempts imported: %d", max(0,after-before))
            return ImportResult(sid,len(events),max(0,after-before),warnings=tuple(warnings))
        except Exception as exc:
            # Separate diagnostic transaction, after the data transaction rolled back.
            with connect(self.repository.path) as db, db:
                db.execute("""INSERT INTO import_snapshots(profile_id,file_sha256,source_path,import_status,error_message)
                              VALUES(?,?,?,'failed',?) ON CONFLICT(profile_id,file_sha256) DO UPDATE SET
                              import_status='failed',error_message=excluded.error_message,imported_at=CURRENT_TIMESTAMP""",
                           (profile_id,snapshot.sha256,source_path,str(exc)))
            log.error("Import failed: %s", type(exc).__name__)
            raise
