from dataclasses import dataclass, field
from typing import Any


@dataclass
class SiiObject:
    object_type: str
    object_id: str
    fields: dict[str, Any]
    raw_fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Event:
    event_type: str
    timestamp: int
    object_id: str
    link: str | None
    fields: dict[str, Any]
    result: dict[str, Any] | None = None
    identity: str = ""


@dataclass
class Attempt:
    scenario_code: str
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    score: float | None = None
    rank_raw: str | None = None
    game_duration_raw: str | None = None
    elapsed_seconds: int | None = None
    result_object_id: str | None = None
    status: str = "unknown"
    match_confidence: str = "unmatched"
    start_identity: str | None = None
    end_identity: str | None = None

    @property
    def logical_identity(self) -> str:
        return "start:" + self.start_identity if self.start_identity else "end:" + str(self.end_identity)
