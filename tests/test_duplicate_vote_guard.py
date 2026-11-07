import pytest
import core.voting as voting


def test_duplicate_vote_is_rejected_before_chain_write(monkeypatch):
    monkeypatch.setattr(voting, "get_election", lambda _eid: {
        "election_id": "e1", "title": "Test", "candidates": ["A", "B"], "status": "OPEN"
    })
    monkeypatch.setattr(voting, "has_voted", lambda _eid, _vid: True)
    def should_not_run(*args, **kwargs):
        raise AssertionError("Blockchain write must not be attempted for a duplicate voter")
    monkeypatch.setattr(voting, "record_ballot", should_not_run)
    with pytest.raises(ValueError, match="already submitted"):
        voting.cast_vote("e1", "voter1", 0)


def test_invalid_candidate_index_is_rejected(monkeypatch):
    monkeypatch.setattr(voting, "get_election", lambda _eid: {
        "election_id": "e1", "title": "Test", "candidates": ["A", "B"], "status": "OPEN"
    })
    monkeypatch.setattr(voting, "has_voted", lambda _eid, _vid: False)
    with pytest.raises(ValueError, match="Invalid candidate"):
        voting.cast_vote("e1", "voter1", 4)
