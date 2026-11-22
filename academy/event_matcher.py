"""Pair in log order, using result scenario; overlapping starts stay ambiguous."""
from academy.models import Attempt, Event


def match_attempts(events: list[Event]) -> list[Attempt]:
    attempts: list[Attempt] = []
    pending: dict[str, list[Attempt]] = {}
    for event in events:
        if event.event_type == "scenario_start":
            scenario = event.link or "unknown"
            attempt = Attempt(scenario, start_timestamp=event.timestamp,
                              status="in_progress", start_identity=event.identity)
            pending.setdefault(scenario, []).append(attempt)
            attempts.append(attempt)
        elif event.event_type == "scenario_end":
            result = event.result or {"values": {}, "raw": {}}
            f, raw = result["values"], result["raw"]
            scenario = f.get("scenario") or "unknown"
            candidates = pending.pop(scenario, [])
            if len(candidates) == 1 and candidates[0].start_timestamp <= event.timestamp:
                attempt = candidates[0]
                attempt.match_confidence = "scenario_and_order"
            else:
                for candidate in candidates:
                    candidate.status = "unknown"
                    candidate.match_confidence = "ambiguous"
                attempt = Attempt(scenario, match_confidence="ambiguous" if candidates else "unmatched")
                attempts.append(attempt)
            attempt.end_timestamp = event.timestamp
            attempt.end_identity = event.identity
            attempt.status = "unknown"
            attempt.score = f.get("scenario_score") if isinstance(f.get("scenario_score"), (int, float)) else None
            attempt.rank_raw = raw.get("scenario_rank")
            attempt.game_duration_raw = raw.get("scenario_duration")
            attempt.result_object_id = event.link
            if attempt.start_timestamp is not None:
                attempt.elapsed_seconds = event.timestamp - attempt.start_timestamp
    return attempts
