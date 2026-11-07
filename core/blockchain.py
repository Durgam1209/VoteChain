import json
from web3 import Web3
from web3.logs import DISCARD
from config import ROOT, RPC_URL, CONTRACT_ADDRESS, CHAIN_ID

ARTIFACT = ROOT / "blockchain" / "artifacts" / "contracts" / "Voting.sol" / "Voting.json"
DEPLOYMENT = ROOT / "blockchain" / "deployment.json"


class TransactionSubmittedError(RuntimeError):
    """Raised when a transaction was broadcast but its hash callback failed."""
    def __init__(self, tx_hash, message):
        super().__init__(message)
        self.tx_hash = tx_hash


def load_contract():
    """Load the deployed VoteChain contract and fail closed if it is absent."""
    if not ARTIFACT.exists():
        raise RuntimeError("Contract artifact not found. Run the Hardhat compile command first.")

    if CONTRACT_ADDRESS:
        address = CONTRACT_ADDRESS
    elif DEPLOYMENT.exists():
        deployment = json.loads(DEPLOYMENT.read_text(encoding="utf-8"))
        address = str(deployment.get("address", "")).strip()
    else:
        address = ""

    if not address:
        raise RuntimeError(
            "VoteChain contract address is missing. Deploy the contract and check blockchain/deployment.json."
        )

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 12}))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to local blockchain at {RPC_URL}.")

    if int(w3.eth.chain_id) != int(CHAIN_ID):
        raise RuntimeError(
            f"Wrong blockchain network: connected chain ID {w3.eth.chain_id}, expected {CHAIN_ID}."
        )

    try:
        checksum_address = Web3.to_checksum_address(address)
    except ValueError as exc:
        raise RuntimeError(f"Invalid VoteChain contract address: {address}") from exc

    bytecode = w3.eth.get_code(checksum_address)
    if not bytecode:
        raise RuntimeError(
            f"No smart contract is deployed at {checksum_address} on chain {w3.eth.chain_id}. "
            "The Hardhat node may have been restarted. Deploy Voting.sol to the currently running node."
        )

    contract = w3.eth.contract(address=checksum_address, abi=artifact["abi"])
    return w3, contract


def initialize_election(election_id: str):
    w3, contract = load_contract()
    account = w3.eth.accounts[0]
    key = Web3.keccak(text=election_id)
    tx = contract.functions.initializeElection(key).transact({"from": account})
    receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=30)
    if receipt.status != 1:
        raise RuntimeError("Election initialization transaction failed.")
    return receipt.transactionHash.hex()


def record_ballot(election_id: str, commitment: str, nullifier: str, on_submitted=None):
    """Submit a ballot and expose its hash before waiting for confirmation.

    The callback lets the local recovery queue persist the transaction hash even
    if waiting for a receipt subsequently times out.
    """
    w3, contract = load_contract()
    account = w3.eth.accounts[0]
    tx_hash = contract.functions.recordBallot(
        Web3.keccak(text=election_id),
        bytes.fromhex(commitment),
        bytes.fromhex(nullifier)
    ).transact({"from": account})
    tx_hex = tx_hash.hex()
    if on_submitted:
        try:
            on_submitted(tx_hex)
        except Exception as exc:
            raise TransactionSubmittedError(
                tx_hex,
                f"Transaction {tx_hex} was broadcast, but the local recovery record could not save its hash: {exc}"
            ) from exc
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    if receipt.status != 1:
        raise RuntimeError(f"Blockchain transaction failed: {tx_hex}")
    return tx_hex


def chain_ballot_count(election_id: str):
    _, contract = load_contract()
    return contract.functions.ballotCount(Web3.keccak(text=election_id)).call()


def transaction_details(tx_hash: str):
    """Return public transaction metadata for a confirmed demo transaction."""
    w3, contract = load_contract()
    tx = w3.eth.get_transaction(tx_hash)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    return {
        "transaction_hash": tx.hash.hex(),
        "block_number": receipt.blockNumber,
        "status": "CONFIRMED" if receipt.status == 1 else "FAILED",
        "gas_used": receipt.gasUsed,
        "sender": tx["from"],
        "contract": tx["to"],
    }


def verify_ballot_receipt(election_id: str, tx_hash: str, commitment: str):
    """Verify that a confirmed tx emitted this election's BallotRecorded event."""
    if len(commitment) != 64:
        raise ValueError("Commitment must be a 64-character SHA-256 hex string.")
    try:
        expected_commitment = bytes.fromhex(commitment)
    except ValueError as exc:
        raise ValueError("Commitment must contain hexadecimal characters only.") from exc
    w3, contract = load_contract()
    receipt = w3.eth.get_transaction_receipt(tx_hash.strip())
    if receipt is None or receipt.status != 1:
        return {"verified": False, "reason": "Transaction is not confirmed."}
    tx = w3.eth.get_transaction(tx_hash.strip())
    if not tx.to or Web3.to_checksum_address(tx.to) != Web3.to_checksum_address(contract.address):
        return {"verified": False, "reason": "Transaction does not target the VoteChain contract."}
    expected_election = Web3.keccak(text=election_id)
    events = contract.events.BallotRecorded().process_receipt(receipt, errors=DISCARD)
    for event in events:
        args = event["args"]
        if bytes(args["electionKey"]) == bytes(expected_election) and bytes(args["commitment"]) == expected_commitment:
            return {
                "verified": True,
                "block_number": receipt.blockNumber,
                "transaction_hash": receipt.transactionHash.hex(),
                "status": "CONFIRMED",
            }
    return {"verified": False, "reason": "No matching ballot commitment event was found in this transaction."}


def transaction_receipt_status(tx_hash: str):
    """Return receipt status; None means the transaction is not yet available."""
    w3, _ = load_contract()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return None
    return {"status": int(receipt.status), "block_number": int(receipt.blockNumber)}
