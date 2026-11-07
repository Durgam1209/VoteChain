import sqlite3

from core import candidate_profiles as profiles


def setup_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(profiles, "DB_PATH", db_path)
    monkeypatch.setattr(profiles, "ROOT", tmp_path)
    monkeypatch.setattr(profiles, "IMAGE_DIR", tmp_path / "data" / "candidate_images")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE elections (election_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO elections VALUES ('TEST-2026')")
    profiles.init_candidate_profiles()
    return db_path


def test_candidate_profile_round_trip(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    profiles.save_candidate_profile(
        "TEST-2026", "Candidate A", "President", "Computer Science", "3rd Year",
        "Improve student services", "More workshops\nBetter labs"
    )
    result = profiles.get_candidate_profile("TEST-2026", "Candidate A")
    assert result["position"] == "President"
    assert result["department"] == "Computer Science"
    assert result["academic_year"] == "3rd Year"
    assert result["manifesto"] == "Improve student services"
    assert "More workshops" in result["promises"]


def test_election_details_round_trip(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    profiles.save_election_details("TEST-2026", "Council President", "Annual student election")
    assert profiles.get_election_details("TEST-2026") == {
        "position_title": "Council President",
        "description": "Annual student election",
    }


def test_invalid_photo_is_rejected(tmp_path, monkeypatch):
    setup_database(tmp_path, monkeypatch)
    try:
        profiles.save_candidate_profile(
            "TEST-2026", "Candidate A", photo_bytes=b"not an image", photo_extension=".png"
        )
    except ValueError as exc:
        assert "content" in str(exc)
    else:
        raise AssertionError("Invalid image content should be rejected")
