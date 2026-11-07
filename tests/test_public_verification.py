from types import SimpleNamespace

import core.blockchain as blockchain


class FakeEvent:
    def __init__(self, events):
        self._events = events

    def process_receipt(self, receipt, errors=0):
        return self._events


class FakeContract:
    address = "0x1234567890123456789012345678901234567890"

    def __init__(self, events):
        self.events = SimpleNamespace(BallotRecorded=lambda: FakeEvent(events))


class FakeEth:
    def __init__(self, receipt, tx):
        self.receipt = receipt
        self.tx = tx

    def get_transaction_receipt(self, tx_hash):
        return self.receipt

    def get_transaction(self, tx_hash):
        return self.tx


def test_public_verifier_matches_election_and_commitment(monkeypatch):
    commitment = "ab" * 32
    election_key = b"e" * 32
    receipt = SimpleNamespace(status=1, blockNumber=42, transactionHash=bytes.fromhex("12" * 32))
    tx = SimpleNamespace(to=FakeContract.address)
    contract = FakeContract([{"args": {"electionKey": election_key, "commitment": bytes.fromhex(commitment)}}])
    monkeypatch.setattr(blockchain.Web3, "keccak", staticmethod(lambda text=None: election_key))
    monkeypatch.setattr(blockchain, "load_contract", lambda: (SimpleNamespace(eth=FakeEth(receipt, tx)), contract))
    result = blockchain.verify_ballot_receipt("DBIT-2026", "0x" + "12" * 32, commitment)
    assert result["verified"] is True
    assert result["block_number"] == 42


def test_public_verifier_rejects_mismatched_commitment(monkeypatch):
    commitment = "ab" * 32
    election_key = b"e" * 32
    receipt = SimpleNamespace(status=1, blockNumber=42, transactionHash=bytes.fromhex("12" * 32))
    tx = SimpleNamespace(to=FakeContract.address)
    contract = FakeContract([{"args": {"electionKey": election_key, "commitment": b"z" * 32}}])
    monkeypatch.setattr(blockchain.Web3, "keccak", staticmethod(lambda text=None: election_key))
    monkeypatch.setattr(blockchain, "load_contract", lambda: (SimpleNamespace(eth=FakeEth(receipt, tx)), contract))
    result = blockchain.verify_ballot_receipt("DBIT-2026", "0x" + "12" * 32, commitment)
    assert result["verified"] is False
