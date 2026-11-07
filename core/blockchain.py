import json
from web3 import Web3
from web3.logs import DISCARD
from eth_account import Account
from config import ROOT, RPC_URL, CONTRACT_ADDRESS, CHAIN_ID, TRANSACTION_PRIVATE_KEY

ARTIFACT = ROOT / "blockchain" / "artifacts" / "contracts" / "Voting.sol" / "Voting.json"
DEPLOYMENT = ROOT / "blockchain" / "deployment.json"


class TransactionSubmittedError(RuntimeError):
    """Raised when a transaction was broadcast but its hash callback failed."""
    def __init__(self, tx_hash, message):
        super().__init__(message)
        self.tx_hash = tx_hash


def load_contract():
    if not ARTIFACT.exists():
        raise RuntimeError("Contract artifact not found. Ensure blockchain/artifacts/contracts/Voting.sol/Voting.json is committed.")

    address = CONTRACT_ADDRESS
    if not address and DEPLOYMENT.exists():
        address = str(json.loads(DEPLOYMENT.read_text(encoding="utf-8")).get("address", "")).strip()
    if not address:
        raise RuntimeError("Contract address missing. Set CONTRACT_ADDRESS in Streamlit Secrets.")

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise RuntimeError("Cannot connect to the configured blockchain RPC. Check RPC_URL in Streamlit Secrets.")
    actual_chain_id = int(w3.eth.chain_id)
    if actual_chain_id != int(CHAIN_ID):
        raise RuntimeError(f"Wrong blockchain network: connected chain ID {actual_chain_id}, expected {CHAIN_ID}.")

    checksum_address = Web3.to_checksum_address(address)
    if not w3.eth.get_code(checksum_address):
        raise RuntimeError(f"No contract code found at {checksum_address} on chain {actual_chain_id}. Verify CONTRACT_ADDRESS and network.")
    contract = w3.eth.contract(address=checksum_address, abi=artifact["abi"])
    return w3, contract


def _send_signed_transaction(w3, function_call):
    if not TRANSACTION_PRIVATE_KEY:
        raise RuntimeError("TRANSACTION_PRIVATE_KEY is missing. Add it to Streamlit Secrets; never commit it to GitHub.")
    account = Account.from_key(TRANSACTION_PRIVATE_KEY)
    if int(w3.eth.chain_id) != int(CHAIN_ID):
        raise RuntimeError("RPC chain ID changed; refusing to sign transaction.")
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = function_call.build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": int(CHAIN_ID),
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    raw_tx = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    return tx_hash


def initialize_election(election_id: str):
    w3, contract = load_contract()
    key = Web3.keccak(text=election_id)
    tx_hash = _send_signed_transaction(w3, contract.functions.initializeElection(key))
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"Election initialization transaction failed: {tx_hash.hex()}")
    return receipt.transactionHash.hex()


def record_ballot(election_id: str, commitment: str, nullifier: str, on_submitted=None):
    w3, contract = load_contract()
    if len(commitment) != 64 or len(nullifier) != 64:
        raise ValueError("Commitment and nullifier must each be 64-character hexadecimal strings.")
    try:
        commitment_bytes = bytes.fromhex(commitment)
        nullifier_bytes = bytes.fromhex(nullifier)
    except ValueError as exc:
        raise ValueError("Commitment and nullifier must contain hexadecimal characters only.") from exc

    tx_hash = _send_signed_transaction(
        w3,
        contract.functions.recordBallot(Web3.keccak(text=election_id), commitment_bytes, nullifier_bytes),
    )
    tx_hex = tx_hash.hex()
    if on_submitted:
        try:
            on_submitted(tx_hex)
        except Exception as exc:
            raise TransactionSubmittedError(tx_hex, f"Transaction {tx_hex} was broadcast, but its recovery record could not save the hash: {exc}") from exc
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        raise RuntimeError(f"Blockchain transaction failed: {tx_hex}")
    return tx_hex


def chain_ballot_count(election_id: str):
    _, contract = load_contract()
    return contract.functions.ballotCount(Web3.keccak(text=election_id)).call()


def transaction_details(tx_hash: str):
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
    if len(commitment) != 64:
        raise ValueError("Commitment must be a 64-character SHA-256 hex string.")
    try:
        expected_commitment = bytes.fromhex(commitment)
    except ValueError as exc:
        raise ValueError("Commitment must contain hexadecimal characters only.") from exc
    w3, contract = load_contract()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash.strip())
    except Exception:
        return {"verified": False, "reason": "Transaction is not confirmed or cannot be found."}
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
            return {"verified": True, "block_number": receipt.blockNumber, "transaction_hash": receipt.transactionHash.hex(), "status": "CONFIRMED"}
    return {"verified": False, "reason": "No matching ballot commitment event was found in this transaction."}


def transaction_receipt_status(tx_hash: str):
    w3, _ = load_contract()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return None
    return {"status": int(receipt.status), "block_number": int(receipt.blockNumber)}
