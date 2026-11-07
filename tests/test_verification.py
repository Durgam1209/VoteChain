from core.verification import ballot_commitment, verify_commitment, make_nullifier

def test_commitment_verifies():
    ballot = ["12345", "67890"]
    commitment = ballot_commitment("e1", ballot)
    assert verify_commitment("e1", ballot, commitment)
    assert not verify_commitment("e1", ["12346", "67890"], commitment)

def test_nullifier_is_deterministic_and_election_scoped():
    a = make_nullifier("e1", "voter1", "secret")
    assert a == make_nullifier("e1", "VOTER1", "secret")
    assert a != make_nullifier("e2", "voter1", "secret")
