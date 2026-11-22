from academy.decoder import Decoder
from academy.sii_parser import parse_sii
from academy.academy_parser import academy_events


def test_reference(reference):
    events = academy_events(parse_sii(Decoder().decode(reference.read_bytes()).text))
    assert events
    ends = [e for e in events if e.event_type == "scenario_end"]
    assert ends and all(e.result for e in ends)


def test_csv_prefix(reference):
    import csv
    from academy.event_matcher import match_attempts
    path = reference.with_name("academy_book_states (1)_proby.csv")
    if not path.exists():
        import pytest
        pytest.skip("Prywatny CSV nie jest dostępny")
    attempts = match_attempts(academy_events(parse_sii(Decoder().decode(reference.read_bytes()).text)))
    with path.open(encoding="utf-8-sig",newline="") as source:
        rows = list(csv.DictReader(source,delimiter=";"))
    assert len(attempts) >= len(rows)
    for actual,expected in zip(attempts,rows):
        assert actual.scenario_code == expected["scenariusz"]
        assert actual.score == float(expected["punkty"])
        assert actual.rank_raw == expected["wynik_rank"]
        assert actual.game_duration_raw == expected["czas_w_pliku"]
        assert actual.elapsed_seconds == int(expected["czas_od_startu_s"])
