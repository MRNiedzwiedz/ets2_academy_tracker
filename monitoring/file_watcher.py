"""Watchdog triggers a serialized import queue; periodic scans retry failures."""
import logging
import os
from pathlib import Path
from threading import Event, Lock
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from monitoring.importer import Importer

log = logging.getLogger(__name__)


def normalize(path):
    return os.path.normcase(os.path.abspath(path))


class FileMonitor:
    def __init__(self, importer: Importer, scan_seconds=5.0, debounce_seconds=1.0, callback=None):
        self.importer = importer
        self.scan_seconds = scan_seconds
        self.debounce_seconds = debounce_seconds
        self.callback = callback or (lambda *args: None)
        self.stop_event = Event()
        self.wake = Event()
        self.lock = Lock()
        self.pending: dict[int,float] = {}
        self.paths: dict[str,list[int]] = {}
        self.observer = Observer()
        self.watched = set()

    def stop(self):
        self.stop_event.set()
        self.wake.set()

    def changed(self, path):
        with self.lock:
            profiles = self.paths.get(normalize(path),[])
            if profiles:
                log.debug("File change detected")
            for pid in profiles:
                self.pending[pid] = time.monotonic() + self.debounce_seconds
        self.wake.set()

    def _refresh(self):
        profiles = self.importer.repository.profiles(enabled=True)
        paths = {}
        for p in profiles:
            paths.setdefault(normalize(p["source_path"]),[]).append(p["id"])
            parent = Path(p["source_path"]).parent
            if parent.is_dir() and str(parent) not in self.watched:
                try:
                    self.observer.schedule(self.handler,str(parent),recursive=False)
                    self.watched.add(str(parent))
                except OSError:
                    log.warning("Watchdog unavailable for a directory; periodic scan remains active")
        enabled = {p["id"] for p in profiles}
        with self.lock:
            self.paths = paths
            self.pending = {pid:due for pid,due in self.pending.items() if pid in enabled}
            for pid in enabled:
                self.pending.setdefault(pid,time.monotonic())

    def run(self):
        monitor = self
        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if event.is_directory or event.event_type not in ("modified","created","moved","deleted","closed"):
                    return
                monitor.changed(event.src_path)
                if getattr(event,"dest_path",None):
                    monitor.changed(event.dest_path)
        self.handler = Handler()
        next_scan = 0.0
        try:
            self.observer.start()
            log.info("Monitoring started")
            self.callback("status", "Monitorowanie aktywne")
            while not self.stop_event.is_set():
                self.wake.clear()
                now = time.monotonic()
                if now >= next_scan:
                    self._refresh()
                    next_scan = now + self.scan_seconds
                with self.lock:
                    ready = [pid for pid,due in self.pending.items() if due <= now]
                    for pid in ready:
                        del self.pending[pid]
                for pid in ready:
                    if self.stop_event.is_set():
                        break
                    # Profile can be disabled while waiting in the queue.
                    if not self.importer.repository.query("SELECT id FROM profiles WHERE id=? AND enabled=1",(pid,)):
                        continue
                    try:
                        result = self.importer.import_file(pid,stop=self.stop_event)
                        if not result.duplicate:
                            self.callback("import",f"Profil {pid}: +{result.new_attempts} prób, {result.events} zdarzeń")
                    except Exception as exc:
                        if not self.stop_event.is_set():
                            log.warning("Import will be retried: %s",type(exc).__name__)
                            self.callback("error",f"Profil {pid}: {exc}")
                            with self.lock:
                                self.pending.setdefault(pid,time.monotonic()+self.scan_seconds)
                self.wake.wait(0.2)
        finally:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.callback("status","Monitorowanie zatrzymane")
