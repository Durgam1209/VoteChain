PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS voters (
    voter_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    password_hash BLOB NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_eligible INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS elections (
    election_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    candidates_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('OPEN','CLOSED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    start_at TEXT,
    end_at TEXT
);

-- Identity eligibility is kept separate from ballot contents.
CREATE TABLE IF NOT EXISTS used_voters (
    election_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    nullifier TEXT NOT NULL,
    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (election_id, voter_id),
    UNIQUE (election_id, nullifier),
    FOREIGN KEY (election_id) REFERENCES elections(election_id),
    FOREIGN KEY (voter_id) REFERENCES voters(voter_id)
);

-- Ballot contents remain separated from voter identity.
CREATE TABLE IF NOT EXISTS ballots (
    ballot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id TEXT NOT NULL,
    encrypted_values_json TEXT NOT NULL,
    commitment TEXT NOT NULL,
    nullifier TEXT NOT NULL,
    tx_hash TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(election_id),
    UNIQUE (election_id, nullifier)
);

-- Local recovery queue. voter_id is retained only in this local operational
-- queue until the transaction is reconciled; it is never written to the chain.
CREATE TABLE IF NOT EXISTS pending_ballots (
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
);
CREATE INDEX IF NOT EXISTS idx_pending_ballots_status ON pending_ballots(status, created_at);
