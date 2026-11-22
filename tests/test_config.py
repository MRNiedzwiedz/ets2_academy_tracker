from config import Config
import pytest


def test_round_trip(tmp_path):
    path = tmp_path/"config.json"
    config = Config(str(tmp_path),bsii_command=["decoder.exe","{input}"])
    config.save(path)
    assert Config.load(path) == config


def test_bad_command():
    with pytest.raises(ValueError):
        Config(bsii_command=["decoder.exe"]).validate()
