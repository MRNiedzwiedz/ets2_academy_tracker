from academy.sii_parser import parse_sii
from academy.academy_parser import academy_events
from academy.event_matcher import match_attempts
from conftest import sii, result

SC = "academy.scenario.book1.test"


def match(events, results=""):
    parsed = academy_events(parse_sii(sii(events, results)))
    for i, e in enumerate(parsed):
        e.identity = str(i)
    return match_attempts(parsed)


def test_two_attempts():
    rows = match([(1,"scenario_start",SC),(2,"scenario_end","r"),(2,"scenario_start",SC),(3,"scenario_end","r")], result())
    assert len(rows) == 2
    assert all(a.status == "unknown" and a.elapsed_seconds == 1 for a in rows)
    assert rows[0].game_duration_raw == "27325"


def test_start_only():
    assert match([(1,"scenario_start",SC)])[0].status == "in_progress"


def test_orphan_end():
    row = match([(2,"scenario_end","r")], result(rank="nil"))[0]
    assert row.start_timestamp is None and row.status == "unknown" and row.rank_raw == "nil"


def test_ambiguous_restart():
    rows = match([(1,"scenario_start",SC),(1,"scenario_start",SC),(2,"scenario_end","r")],result())
    assert len(rows) == 3
    assert all(a.match_confidence == "ambiguous" for a in rows)


def test_missing_result():
    assert match([(1,"scenario_end","missing")])[0].scenario_code == "unknown"
