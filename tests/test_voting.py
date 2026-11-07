import pytest
from core.voting import create_election, get_election

def test_election_creation(tmp_path, monkeypatch):
    import core.voting as voting
    monkeypatch.setattr(voting, "initialize_election", lambda election_id: "test-tx")
    import database.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite")
    db.init_db()
    # Create the required voter table rows are not needed for election creation.
    create_election("election-1", "Demo Election", ["A", "B"])
    assert get_election("election-1")["status"] == "OPEN"
    with pytest.raises(ValueError):
        create_election("election-2", "Bad Election", ["A", "A"])
