"""Read-only diagnostic CLI; does not create decoded files next to game saves."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from academy.decoder import Decoder
from academy.academy_parser import academy_events
from academy.sii_parser import parse_sii
from academy.event_matcher import match_attempts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    decoded = Decoder().decode(args.source.read_bytes())
    objects = parse_sii(decoded.text)
    events = academy_events(objects)
    for i,e in enumerate(events):
        e.identity = str(i)
    attempts = match_attempts(events)
    print(json.dumps({"format":decoded.source_format,"warnings":decoded.warnings,
                      "objects":dict(Counter(o.object_type for o in objects.values())),
                      "events":len(events),"attempts":len(attempts),
                      "scenarios":dict(Counter(a.scenario_code for a in attempts)),
                      "statuses":dict(Counter(a.status for a in attempts))},indent=2,ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
