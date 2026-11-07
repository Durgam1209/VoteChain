from datetime import datetime, timedelta

import pytest

import database.db as db
import core.voting as voting
from core.authentication import create_user, authenticate, set_voter_eligibility


def setup_test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "votechain-test.sqlite3")
    db.init_db()
    return tmp_path / "votechain-test.sqlite3"


def test_existing_schema_migration_adds_schedule_and_eligibility(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", path)
    import sqlite3
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE voters(voter_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, password_hash BLOB NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0)")
        conn.execute("CREATE TABLE elections(election_id TEXT PRIMARY KEY,title TEXT NOT NULL,candidates_json TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT INTO voters(voter_id,display_name,password_hash) VALUES('legacy','Legacy',X'01')")
        conn.execute("INSERT INTO elections(election_id,title,candidates_json,status) VALUES('old','Old','[\"A\",\"B\"]','OPEN')")
    db.init_db()
    voter_cols = {r["name"] for r in db.fetchall("PRAGMA table_info(voters)")}
    election_cols = {r["name"] for r in db.fetchall("PRAGMA table_info(elections)")}
    assert "is_eligible" in voter_cols
    assert {"start_at", "end_at"}.issubset(election_cols)
    assert db.fetchone("SELECT is_eligible FROM voters WHERE voter_id='legacy'")[0] == 1


def test_new_registration_requires_admin_approval(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    create_user("new-voter", "New Voter", "strong-pass-123", eligible=False)
    assert authenticate("new-voter", "strong-pass-123")["pending_approval"] is True
    set_voter_eligibility("new-voter", True)
    assert authenticate("new-voter", "strong-pass-123")["voter_id"] == "new-voter"
    set_voter_eligibility("new-voter", False)
    assert authenticate("new-voter", "strong-pass-123")["pending_approval"] is True


def test_scheduled_election_blocks_before_start_and_after_end():
    now = datetime.now().replace(microsecond=0)
    election = {"status": "OPEN", "start_at": (now + timedelta(hours=1)).isoformat(),
                "end_at": (now + timedelta(hours=2)).isoformat()}
    assert voting.election_state(election) == "SCHEDULED"
    election["start_at"] = (now - timedelta(hours=1)).isoformat()
    election["end_at"] = (now - timedelta(minutes=1)).isoformat()
    assert voting.election_state(election) == "ENDED"
    election["end_at"] = (now + timedelta(hours=1)).isoformat()
    assert voting.election_state(election) == "OPEN"


def test_create_election_rejects_invalid_schedule(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    monkeypatch.setattr(voting, "initialize_election", lambda _eid: "0x-demo")
    now = datetime.now().replace(microsecond=0)
    with pytest.raises(ValueError, match="later than"):
        voting.create_election("election-1", "Demo", ["A", "B"], now, now - timedelta(minutes=1))


def test_ineligible_voter_is_blocked_before_chain_write(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    create_user("pending-voter", "Pending Voter", "strong-pass-123", eligible=False)
    monkeypatch.setattr(voting, "get_election", lambda _eid: {
        "election_id": "e1", "title": "Demo", "candidates": ["A", "B"],
        "status": "OPEN", "start_at": None, "end_at": None,
    })
    monkeypatch.setattr(voting, "has_voted", lambda _eid, _vid: False)
    monkeypatch.setattr(voting, "record_ballot", lambda *a, **k: (_ for _ in ()).throw(AssertionError("chain write must not occur")))
    with pytest.raises(ValueError, match="not approved"):
        voting.cast_vote("e1", "pending-voter", 0)


def test_confirmed_vote_is_finalized_from_recovery_queue(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    create_user("eligible-voter", "Eligible Voter", "strong-pass-123", eligible=True)
    with db.connect() as conn:
        conn.execute("INSERT INTO elections(election_id,title,candidates_json,status) VALUES('e1','Demo','[\"A\",\"B\"]','OPEN')")
    monkeypatch.setattr(voting, "_nullifier_secret", lambda: "secret")
    monkeypatch.setattr(voting, "encrypt_ballot", lambda _index, _count: ["111", "222"])
    monkeypatch.setattr(voting, "ballot_commitment", lambda _eid, _values: "a" * 64)
    monkeypatch.setattr(voting, "make_nullifier", lambda _eid, _vid, _secret: "b" * 64)

    def fake_record(_eid, _commitment, _nullifier, on_submitted=None):
        if on_submitted:
            on_submitted("0xabc123")
        return "0xabc123"

    monkeypatch.setattr(voting, "record_ballot", fake_record)
    result = voting.cast_vote("e1", "eligible-voter", 0)
    assert result["tx_hash"] == "0xabc123"
    assert voting.has_voted("e1", "eligible-voter")
    assert len(voting.election_ballots("e1")) == 1
    pending = db.fetchone("SELECT status FROM pending_ballots WHERE election_id='e1'")
    assert pending["status"] == "CONFIRMED"


def test_reconciliation_completes_a_confirmed_pending_ballot(tmp_path, monkeypatch):
    setup_test_db(tmp_path, monkeypatch)
    create_user("eligible-voter", "Eligible Voter", "strong-pass-123", eligible=True)
    with db.connect() as conn:
        conn.execute("INSERT INTO elections(election_id,title,candidates_json,status) VALUES('e1','Demo','[\"A\",\"B\"]','OPEN')")
        conn.execute("INSERT INTO pending_ballots(election_id,voter_id,encrypted_values_json,commitment,nullifier,tx_hash,status) VALUES('e1','eligible-voter','[\"111\",\"222\"]',?,?,?,'REVIEW')",
                     ("a" * 64, "b" * 64, "0xabc123"))
    monkeypatch.setattr(voting, "transaction_receipt_status", lambda _tx: {"status": 1, "block_number": 42})
    result = voting.reconcile_pending_ballot(1)
    assert result["status"] == "CONFIRMED"
    assert len(voting.election_ballots("e1")) == 1
    assert voting.has_voted("e1", "eligible-voter")
