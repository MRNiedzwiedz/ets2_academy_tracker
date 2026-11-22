import hashlib
import pytest
from database.repository import Repository
from monitoring.importer import Importer
from monitoring.snapshot import Snapshot
from conftest import sii, result

SC = "academy.scenario.book1.test"


def snapshot(text):
    raw = text.encode()
    return Snapshot(raw,hashlib.sha256(raw).hexdigest())


@pytest.fixture
def setup(tmp_path):
    repo = Repository(tmp_path/"test.db")
    pid = repo.add_profile(repo.add_user("Test"),"ETS2",str(tmp_path/"input.sii"))
    return repo,pid,Importer(repo)


def test_reimport_and_restart(setup):
    repo,pid,imp = setup
    snap = snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result()))
    assert imp.import_snapshot(pid,snap).new_attempts == 1
    assert Importer(Repository(repo.path)).import_snapshot(pid,snap).duplicate
    assert len(repo.attempts()) == 1


def test_new_version_and_truncated_history(setup):
    repo,pid,imp = setup
    imp.import_snapshot(pid,snapshot(sii([(1,"scenario_start",SC)])))
    imp.import_snapshot(pid,snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result())))
    assert len(repo.attempts()) == 1
    assert repo.attempts()[0]["end_timestamp"] == 2
    imp.import_snapshot(pid,snapshot(sii([(3,"scenario_start",SC),(4,"scenario_end","r")],result())))
    rows = repo.attempts()
    assert [r["attempt_number"] for r in rows] == [1,2]
    assert rows[0]["visible_in_latest"] == 0 and rows[1]["visible_in_latest"] == 1


def test_allocator_rename_and_same_time_collisions(setup):
    repo,pid,imp = setup
    text = sii([(1,"scenario_start",SC),(1,"scenario_end","_nameless.r"),
                (1,"scenario_start",SC),(1,"scenario_end","_nameless.r")],result("_nameless.r"))
    imp.import_snapshot(pid,snapshot(text))
    imp.import_snapshot(pid,snapshot(text.replace("_nameless.r","_nameless.changed")))
    assert len(repo.attempts()) == 2
    assert len(repo.query("SELECT * FROM academy_events")) == 4


def test_rollback_and_retry(setup,monkeypatch):
    repo,pid,imp = setup
    snap = snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result()))
    import monitoring.importer as module
    original = module.match_attempts
    def fail(events):
        raise RuntimeError("injected failure")
    monkeypatch.setattr(module,"match_attempts",fail)
    with pytest.raises(RuntimeError):
        imp.import_snapshot(pid,snap)
    assert not repo.attempts() and not repo.query("SELECT * FROM academy_events")
    assert repo.query("SELECT import_status FROM import_snapshots")[0]["import_status"] == "failed"
    monkeypatch.setattr(module,"match_attempts",original)
    assert imp.import_snapshot(pid,snap).new_attempts == 1


def test_real_database(setup,reference):
    repo,pid,imp = setup
    raw = reference.read_bytes()
    imp.import_snapshot(pid,Snapshot(raw,hashlib.sha256(raw).hexdigest()))
    assert len(repo.attempts()) == 21
    assert all(r["status"] == "unknown" for r in repo.attempts())


def test_late_start_snapshot_enriches_orphan(setup):
    repo,pid,imp = setup
    imp.import_snapshot(pid,snapshot(sii([(2,"scenario_end","r")],result())))
    imp.import_snapshot(pid,snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result())))
    rows = repo.attempts()
    assert len(rows) == 1
    assert rows[0]["start_timestamp"] == 1 and rows[0]["elapsed_seconds"] == 1


def test_profiles_are_independent(setup,tmp_path):
    repo,pid,imp = setup
    other = repo.add_profile(repo.add_user("B"),"Other",str(tmp_path/"other.sii"))
    snap = snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result()))
    imp.import_snapshot(pid,snap)
    imp.import_snapshot(other,snap)
    assert len(repo.attempts()) == 2
    assert all(r["attempt_number"] == 1 for r in repo.attempts())


def test_conflicting_order_rolls_back(setup):
    repo,pid,imp = setup
    imp.import_snapshot(pid,snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result())))
    from academy.exceptions import ParseError
    with pytest.raises(ParseError):
        imp.import_snapshot(pid,snapshot(sii([(2,"scenario_end","r"),(1,"scenario_start",SC)],result())))
    assert len(repo.attempts()) == 1
    assert repo.query("SELECT count(*) n FROM import_snapshots WHERE import_status='processed'")[0]["n"] == 1


def test_missing_result_recovers_without_duplicate_attempt(setup):
    repo,pid,imp = setup
    events = [(1,"scenario_start",SC),(2,"scenario_end","_nameless.r")]
    imp.import_snapshot(pid,snapshot(sii(events)))
    assert len(repo.attempts()) == 2  # unresolved start and orphan end
    full = sii(events,result("_nameless.r"))
    imp.import_snapshot(pid,snapshot(full))
    assert len(repo.attempts()) == 1
    assert repo.attempts()[0]["elapsed_seconds"] == 1
    assert len(repo.query("SELECT * FROM attempt_reconciliations")) == 1
    imp.import_snapshot(pid,snapshot(full.replace("_nameless.r","_nameless.renamed")))
    assert len(repo.attempts()) == 1


def test_orphan_result_recovers_scenario_number(setup):
    repo,pid,imp = setup
    imp.import_snapshot(pid,snapshot(sii([(1,"scenario_start",SC),(2,"scenario_end","r")],result())))
    imp.import_snapshot(pid,snapshot(sii([(3,"scenario_end","_nameless.missing")],"")))
    imp.import_snapshot(pid,snapshot(sii([(3,"scenario_end","_nameless.missing")],result("_nameless.missing"))))
    rows = repo.attempts()
    assert len(rows) == 2
    assert [r["attempt_number"] for r in rows] == [1,2]
