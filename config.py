from dataclasses import asdict, dataclass, field
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def default_data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "ETS2AcademyTracker"


@dataclass
class Config:
    data_dir: str = field(default_factory=lambda: str(default_data_dir()))
    scan_seconds: float = 5.0
    debounce_seconds: float = 1.0
    bsii_command: list[str] = field(default_factory=list)
    log_level: str = "INFO"

    def validate(self):
        if not 1 <= self.scan_seconds <= 3600 or not 0.1 <= self.debounce_seconds <= 60:
            raise ValueError("Skan: 1–3600 s; debounce: 0,1–60 s")
        if not isinstance(self.bsii_command, list) or not all(isinstance(v,str) for v in self.bsii_command):
            raise ValueError("bsii_command musi być tablicą argumentów JSON")
        if self.bsii_command and not any("{input}" in v for v in self.bsii_command):
            raise ValueError("bsii_command wymaga {input}")
        if self.log_level not in ("DEBUG","INFO","WARNING","ERROR"):
            raise ValueError("Niepoprawny poziom logowania")
        if not self.data_dir.strip():
            raise ValueError("Podaj katalog danych")

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            return cls()
        config = cls(**json.loads(path.read_text(encoding="utf-8")))
        config.validate()
        return config

    def save(self, path: Path):
        self.validate()
        path.parent.mkdir(parents=True,exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self),indent=2,ensure_ascii=False),encoding="utf-8")
        temp.replace(path)


def configure_logging(config: Config):
    folder = Path(config.data_dir)
    folder.mkdir(parents=True,exist_ok=True)
    handler = RotatingFileHandler(folder / "tracker.log",maxBytes=2_000_000,backupCount=3,encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=config.log_level,handlers=[handler],force=True)
