from core.encryption import encrypt_ballot, aggregate_ciphertexts, decrypt_tally

def test_paillier_homomorphic_tally():
    ballots = [
        encrypt_ballot(0, 3),
        encrypt_ballot(1, 3),
        encrypt_ballot(0, 3),
        encrypt_ballot(2, 3),
    ]
    aggregate = aggregate_ciphertexts(ballots)
    assert decrypt_tally(aggregate) == [2, 1, 1]
