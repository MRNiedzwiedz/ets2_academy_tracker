from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
from threading import Event
import time
from academy.decoder import MAX_SIZE
from academy.exceptions import SnapshotError


@dataclass(frozen=True)
class Snapshot:
    raw: bytes
    sha256: str


def stable_snapshot(path: Path, settle: float = 0.35, stop: Event | None = None) -> Snapshot:
    def fingerprint():
        stat = path.stat()
        if stat.st_size > MAX_SIZE:
            raise SnapshotError("Plik przekracza limit 64 MiB")
        return stat.st_size, stat.st_mtime_ns, stat.st_ino

    try:
        before = fingerprint()
        if stop:
            if stop.wait(settle):
                raise SnapshotError("Odczyt zatrzymany")
        else:
            time.sleep(settle)
        if fingerprint() != before:
            raise SnapshotError("Plik jest zapisywany; import zostanie ponowiony")
        with path.open("rb") as source:
            raw = source.read(MAX_SIZE + 1)
        if fingerprint() != before or len(raw) != before[0]:
            raise SnapshotError("Plik zmienił się podczas odczytu")
        snapshot = Snapshot(raw, hashlib.sha256(raw).hexdigest())
        logging.getLogger(__name__).debug("Snapshot SHA256 computed")
        return snapshot
    except OSError as exc:
        raise SnapshotError("Plik nie jest dostępny do odczytu") from exc
