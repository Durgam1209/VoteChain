import pytest
from database.db import init_db
from core.authentication import create_user, authenticate

def test_password_authentication(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.sqlite")
    # db module imported DB_PATH directly, patch its reference too.
    import database.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite")
    init_db()
    create_user("voter1", "Voter One", "strong-pass-123")
    assert authenticate("voter1", "strong-pass-123")["voter_id"] == "voter1"
    assert authenticate("voter1", "wrong-password") is None
    with pytest.raises(ValueError):
        create_user("voter1", "Duplicate", "strong-pass-123")
