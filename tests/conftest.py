from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reference():
    path = ROOT / "academy_book_states (2).sii"
    if not path.exists():
        pytest.skip("Prywatny referencyjny zapis SII nie jest dostępny")
    return path


def sii(events, results=""):
    refs = "\n".join(f"entries[{i}]: e{i}" for i in range(len(events)))
    units = "\n".join(f"academy_log_entry : e{i} {{ time: {t} type: {kind} link: {link} }}"
                      for i, (t, kind, link) in enumerate(events))
    return f"SiiNunit {{ academy_log : log {{ entries: {len(events)} {refs} }} {units} {results} }}"


def result(oid="r", scenario="academy.scenario.book1.test", rank="0"):
    return f"academy_scenario_result : {oid} {{ scenario: {scenario} scenario_score: 9 scenario_rank: {rank} scenario_duration: 27325 }}"
