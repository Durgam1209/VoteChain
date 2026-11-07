import json
from phe import paillier
from config import KEY_PATH

def load_or_create_keys():
    if KEY_PATH.exists():
        data = json.loads(KEY_PATH.read_text(encoding="utf-8"))
        pub = paillier.PaillierPublicKey(n=int(data["n"]))
        priv = paillier.PaillierPrivateKey(pub, p=int(data["p"]), q=int(data["q"]))
        return pub, priv
    pub, priv = paillier.generate_paillier_keypair(n_length=1024)
    KEY_PATH.write_text(json.dumps({
        "n": str(pub.n), "p": str(priv.p), "q": str(priv.q)
    }, indent=2), encoding="utf-8")
    return pub, priv

def encrypt_ballot(candidate_index: int, candidate_count: int):
    if candidate_count < 2 or not 0 <= candidate_index < candidate_count:
        raise ValueError("Invalid candidate selection.")
    pub, _ = load_or_create_keys()
    vector = [1 if i == candidate_index else 0 for i in range(candidate_count)]
    encrypted = [str(pub.encrypt(value).ciphertext(be_secure=True)) for value in vector]
    return encrypted

def aggregate_ciphertexts(ballot_vectors):
    if not ballot_vectors:
        raise ValueError("There are no ballots to tally.")
    pub, _ = load_or_create_keys()
    count = len(ballot_vectors[0])
    if any(len(v) != count for v in ballot_vectors):
        raise ValueError("Ballot dimensions do not match.")
    n_sq = pub.n * pub.n
    totals = [1] * count
    for vector in ballot_vectors:
        for i, ciphertext in enumerate(vector):
            c = int(ciphertext)
            if not 0 < c < n_sq:
                raise ValueError("Invalid ciphertext.")
            totals[i] = (totals[i] * c) % n_sq
    return [str(c) for c in totals]

def decrypt_tally(aggregated):
    _, priv = load_or_create_keys()
    return [int(priv.raw_decrypt(int(c))) for c in aggregated]
