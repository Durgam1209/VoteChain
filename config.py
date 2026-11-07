from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
KEY_DIR = DATA_DIR / "keys"
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "votechain.sqlite3")))
KEY_PATH = Path(os.getenv("PAILLIER_KEY_PATH", str(KEY_DIR / "paillier_keys.json")))
NULLIFIER_SECRET_PATH = Path(os.getenv("NULLIFIER_SECRET_PATH", str(KEY_DIR / "nullifier_secret.txt")))
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "").strip()
CHAIN_ID = int(os.getenv("CHAIN_ID", "31337"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
KEY_DIR.mkdir(parents=True, exist_ok=True)
