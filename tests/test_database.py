import sqlite3
import pytest
from database.repository import Repository


def test_users_profiles_and_fk(tmp_path):
    repo = Repository(tmp_path/"test.db")
    a,b = repo.add_user("A"),repo.add_user("B")
    repo.add_profile(a,"ETS1",str(tmp_path/"one.sii"))
    repo.add_profile(b,"ETS2",str(tmp_path/"two.sii"))
    assert len(repo.profiles()) == 2
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_profile(1234,"missing user","x.sii")
