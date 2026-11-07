import sqlite3
from config import DB_PATH, ROOT


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 20000")
    return conn


def init_db():
    with connect() as conn:
        schema = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
        conn.executescript(schema)
        # Additive migrations for databases created by earlier VoteChain builds.
        voter_columns = {r["name"] for r in conn.execute("PRAGMA table_info(voters)")}
        if "is_eligible" not in voter_columns:
            # Existing accounts remain eligible to preserve the working demo.
            conn.execute("ALTER TABLE voters ADD COLUMN is_eligible INTEGER NOT NULL DEFAULT 1")
        election_columns = {r["name"] for r in conn.execute("PRAGMA table_info(elections)")}
        if "start_at" not in election_columns:
            conn.execute("ALTER TABLE elections ADD COLUMN start_at TEXT")
        if "end_at" not in election_columns:
            conn.execute("ALTER TABLE elections ADD COLUMN end_at TEXT")
        conn.execute("""CREATE TABLE IF NOT EXISTS pending_ballots (
            pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_id TEXT NOT NULL,
            voter_id TEXT NOT NULL,
            encrypted_values_json TEXT NOT NULL,
            commitment TEXT NOT NULL,
            nullifier TEXT NOT NULL,
            tx_hash TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','REVIEW','CONFIRMED','FAILED')),
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (election_id, nullifier),
            FOREIGN KEY (election_id) REFERENCES elections(election_id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_ballots_status ON pending_ballots(status, created_at)")


def fetchall(query, params=()):
    with connect() as conn:
        return conn.execute(query, params).fetchall()


def fetchone(query, params=()):
    with connect() as conn:
        return conn.execute(query, params).fetchone()
