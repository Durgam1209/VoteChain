from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _secret(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets when available, otherwise environment/.env."""
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
NULLIFIER_SECRET_PATH = Path(_secret("NULLIFIER_SECRET_PATH", str(KEY_DIR / "nullifier_secret.txt")))
RPC_URL = _secret("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = _secret("CONTRACT_ADDRESS", "")
CHAIN_ID = int(_secret("CHAIN_ID", "31337"))
TRANSACTION_PRIVATE_KEY = _secret("TRANSACTION_PRIVATE_KEY", "")

DATA_DIR.mkdir(parents=True, exist_ok=True)
KEY_DIR.mkdir(parents=True, exist_ok=True)
