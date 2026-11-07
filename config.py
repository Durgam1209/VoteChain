
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _secret(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then environment/.env."""
    value = os.getenv(name, default)

    try:
        import streamlit as st
        secret_value = st.secrets.get(name, None)
        if secret_value is not None and str(secret_value).strip():
            value = str(secret_value)
    except Exception:
        pass

    return str(value).strip()


DATA_DIR = ROOT / "data"
KEY_DIR = DATA_DIR / "keys"

DB_PATH = Path(_secret("DB_PATH", str(DATA_DIR / "votechain.sqlite3")))
KEY_PATH = Path(_secret("PAILLIER_KEY_PATH", str(KEY_DIR / "paillier_keys.json")))
NULLIFIER_SECRET_PATH = Path(
    _secret("NULLIFIER_SECRET_PATH", str(KEY_DIR / "nullifier_secret.txt"))
)

# Default to Sepolia, never silently fall back to localhost.
RPC_URL = _secret("RPC_URL", "")
CONTRACT_ADDRESS = _secret("CONTRACT_ADDRESS", "")
CHAIN_ID = int(_secret("CHAIN_ID", "11155111"))
TRANSACTION_PRIVATE_KEY = _secret("TRANSACTION_PRIVATE_KEY", "")

if not RPC_URL:
    raise RuntimeError(
        "RPC_URL is missing. Configure the Sepolia RPC URL in Streamlit Secrets."
    )

if CHAIN_ID != 11155111:
    raise RuntimeError(
        f"VoteChain hosted deployment expects Sepolia (11155111), got {CHAIN_ID}."
    )

if not CONTRACT_ADDRESS:
    raise RuntimeError("CONTRACT_ADDRESS is missing from Streamlit Secrets.")

DATA_DIR.mkdir(parents=True, exist_ok=True)
KEY_DIR.mkdir(parents=True, exist_ok=True)
