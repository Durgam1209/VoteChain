from core.voting import get_election, election_ballots
from core.encryption import aggregate_ciphertexts, decrypt_tally
from core.verification import verify_commitment

def tally_election(election_id):
    election = get_election(election_id)
    if not election or election["status"] != "CLOSED":
        raise ValueError("Close the election before tallying.")
    ballots = election_ballots(election_id)
    if not ballots:
        raise ValueError("No ballots were submitted.")
    for ballot in ballots:
        if not verify_commitment(election_id, ballot["encrypted_values"], ballot["commitment"]):
            raise ValueError("A ballot commitment failed verification.")
    aggregate = aggregate_ciphertexts([b["encrypted_values"] for b in ballots])
    totals = decrypt_tally(aggregate)
    if sum(totals) != len(ballots):
        raise ValueError("Tally integrity check failed.")
    return {"totals": dict(zip(election["candidates"], totals)),
            "ballot_count": len(ballots), "verified": True}
