from pathlib import Path
from threading import Thread,Event
import time
import pytest
from academy.exceptions import SnapshotError
from database.repository import Repository
from monitoring.file_watcher import FileMonitor
from monitoring.importer import Importer
from monitoring.snapshot import stable_snapshot
from conftest import sii,result


def test_stable_read_detects_change(tmp_path,monkeypatch):
    path = tmp_path/"file.sii"
    path.write_bytes(b"first")
    monkeypatch.setattr("monitoring.snapshot.time.sleep",lambda _:path.write_bytes(b"second version"))
    with pytest.raises(SnapshotError):
        stable_snapshot(path)


def test_periodic_monitor_retries_partial_and_replacement(tmp_path):
    source = tmp_path/"academy_book_states.sii"
    source.write_text("SiiNunit {",encoding="utf-8")
    repo = Repository(tmp_path/"test.db")
    pid = repo.add_profile(repo.add_user("A"),"ETS",str(source))
    monitor = FileMonitor(Importer(repo),scan_seconds=.15,debounce_seconds=.05)
    thread = Thread(target=monitor.run)
    thread.start()
    def until(predicate,seconds=8):
        end = time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():
                return True
            time.sleep(.05)
        return False
    try:
        assert until(lambda:repo.query("SELECT id FROM import_snapshots WHERE import_status='failed'"))
        replacement = tmp_path/"replacement.sii"
        replacement.write_text(sii([(1,"scenario_start","academy.scenario.book1.test"),(2,"scenario_end","r")],result()),encoding="utf-8")
        replacement.replace(source)
        assert until(lambda:len(repo.attempts())==1)
        time.sleep(.5)
        assert len(repo.attempts()) == 1
    finally:
        monitor.stop()
        thread.join(timeout=5)
    assert not thread.is_alive()
