import hashlib
import json

def canonical_ballot(election_id: str, encrypted_values: list[str]) -> bytes:
    payload = {"election_id": election_id, "encrypted_values": encrypted_values}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

def ballot_commitment(election_id: str, encrypted_values: list[str]) -> str:
    return hashlib.sha256(canonical_ballot(election_id, encrypted_values)).hexdigest()

def make_nullifier(election_id: str, voter_id: str, secret: str) -> str:
    # Demo-only identity-scoped nullifier. Production requires a stronger
    # anonymous credential / blind-signature or ZK design.
    message = f"{election_id}:{voter_id.strip().lower()}".encode()
    return hashlib.sha256(secret.encode() + b":" + message).hexdigest()

def verify_commitment(election_id: str, encrypted_values: list[str], expected: str) -> bool:
    return ballot_commitment(election_id, encrypted_values) == expected
