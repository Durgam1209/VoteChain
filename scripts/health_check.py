"""Quick local VoteChain dependency and configuration check."""
from pathlib import Path
import sys

from config import DB_PATH, KEY_PATH, NULLIFIER_SECRET_PATH, RPC_URL, CONTRACT_ADDRESS
from database.db import init_db


def main():
    print("VoteChain local health check")
    print("=" * 34)
    try:
        init_db()
        print(f"[OK] SQLite database: {DB_PATH}")
        from database.db import fetchone
        pending = fetchone("SELECT COUNT(*) AS n FROM pending_ballots WHERE status IN ('PENDING','REVIEW')")
        print(f"[INFO] Pending ballot transactions: {pending['n']}")
    except Exception as exc:
        print(f"[FAIL] SQLite: {exc}")
        return 1
    print(f"[INFO] Paillier key exists: {KEY_PATH.exists()}")
    print(f"[INFO] Nullifier secret exists: {NULLIFIER_SECRET_PATH.exists()}")
    print(f"[INFO] RPC endpoint: {RPC_URL}")
    try:
        from core.blockchain import load_contract
        w3, contract = load_contract()
        print(f"[OK] Blockchain connected · chain ID {w3.eth.chain_id} · block {w3.eth.block_number}")
        print(f"[OK] Voting contract: {contract.address}")
        if CONTRACT_ADDRESS:
            print("[INFO] Contract address loaded from .env")
    except Exception as exc:
        print(f"[WARN] Blockchain not ready: {exc}")
        print("Start the Hardhat node and confirm deployment.json exists.")
    print("\nHealth check complete. Warnings do not necessarily mean the UI cannot start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
