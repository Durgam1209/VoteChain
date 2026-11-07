import json
import secrets
from datetime import datetime, timezone

from config import NULLIFIER_SECRET_PATH
from database.db import connect, fetchone, fetchall
from core.encryption import encrypt_ballot
from core.verification import ballot_commitment, make_nullifier
from core.blockchain import record_ballot, initialize_election, transaction_receipt_status


def _nullifier_secret() -> str:
    """Load a persistent local demo secret; never rotate it for an existing DB."""
    if NULLIFIER_SECRET_PATH.exists():
        value = NULLIFIER_SECRET_PATH.read_text(encoding="utf-8").strip()
        if len(value) >= 64:
            return value
        raise RuntimeError("The local nullifier secret file is invalid. Restore it from backup.")
    value = secrets.token_hex(32)
    NULLIFIER_SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    NULLIFIER_SECRET_PATH.write_text(value, encoding="utf-8")
    try:
        NULLIFIER_SECRET_PATH.chmod(0o600)
    except OSError:
        pass
    return value


def _schedule_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.isoformat(timespec="seconds")


def _parse_schedule(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def election_state(election):
    """Computed display state. CLOSED remains an explicit admin decision."""
    if not election:
        return "NOT_FOUND"
    if election["status"] == "CLOSED":
        return "CLOSED"
    now = datetime.now().astimezone().replace(tzinfo=None)
    start_at = _parse_schedule(election.get("start_at"))
    end_at = _parse_schedule(election.get("end_at"))
    if start_at and now < start_at:
        return "SCHEDULED"
    if end_at and now >= end_at:
        return "ENDED"
    return "OPEN"


def voting_window_open(election):
    return election_state(election) == "OPEN"


def create_election(election_id: str, title: str, candidates: list[str], start_at=None, end_at=None):
    candidates = [c.strip() for c in candidates if c.strip()]
    if not election_id or not election_id.strip():
        raise ValueError("Enter an election ID.")
    if not title or not title.strip():
        raise ValueError("Enter an election title.")
    if len(candidates) < 2 or len(set(candidates)) != len(candidates):
        raise ValueError("Provide at least two unique candidate names.")
    start_value = _schedule_value(start_at)
    end_value = _schedule_value(end_at)
    if start_value and end_value and _parse_schedule(end_value) <= _parse_schedule(start_value):
        raise ValueError("Election end time must be later than its start time.")
    election_id = election_id.strip()
    # Keep local creation atomic with the chain initialization result. If the
    # local insert fails, the error is explicit and the deployment can be audited.
    initialize_election(election_id)
    with connect() as conn:
        conn.execute(
            "INSERT INTO elections(election_id,title,candidates_json,status,start_at,end_at) VALUES(?,?,?,'OPEN',?,?)",
            (election_id, title.strip(), json.dumps(candidates), start_value, end_value)
        )


def update_election_schedule(election_id, start_at, end_at):
    start_value = _schedule_value(start_at)
    end_value = _schedule_value(end_at)
    if start_value and end_value and _parse_schedule(end_value) <= _parse_schedule(start_value):
        raise ValueError("Election end time must be later than its start time.")
    with connect() as conn:
        row = conn.execute("SELECT status FROM elections WHERE election_id=?", (election_id,)).fetchone()
        if not row:
            raise ValueError("Election not found.")
        if row["status"] == "CLOSED":
            raise ValueError("A closed election's schedule cannot be changed.")
        count = conn.execute("SELECT COUNT(*) AS n FROM ballots WHERE election_id=?", (election_id,)).fetchone()["n"]
        pending_count = conn.execute(
            "SELECT COUNT(*) AS n FROM pending_ballots WHERE election_id=? AND status IN ('PENDING','REVIEW','CONFIRMED')",
            (election_id,)
        ).fetchone()["n"]
        if count or pending_count:
            raise ValueError("Schedule cannot be changed after ballot submission has started.")
        conn.execute("UPDATE elections SET start_at=?, end_at=? WHERE election_id=?",
                     (start_value, end_value, election_id))


def get_elections():
    rows = fetchall("SELECT * FROM elections ORDER BY created_at DESC")
    return [{
        "election_id": r["election_id"], "title": r["title"],
        "candidates": json.loads(r["candidates_json"]), "status": r["status"],
        "created_at": r["created_at"], "start_at": r["start_at"], "end_at": r["end_at"]
    } for r in rows]


def get_election(election_id):
    row = fetchone("SELECT * FROM elections WHERE election_id=?", (election_id,))
    if not row:
        return None
    return {"election_id": row["election_id"], "title": row["title"],
            "candidates": json.loads(row["candidates_json"]), "status": row["status"],
            "created_at": row["created_at"], "start_at": row["start_at"], "end_at": row["end_at"]}


def cast_vote(election_id: str, voter_id: str, candidate_index: int):
    election = get_election(election_id)
    if not election or not voting_window_open(election):
        raise ValueError("This election is not currently within its voting window.")
    if has_voted(election_id, voter_id):
        raise ValueError("This voter has already submitted a ballot or has a submission awaiting reconciliation.")
    if not isinstance(candidate_index, int) or not 0 <= candidate_index < len(election["candidates"]):
        raise ValueError("Invalid candidate selection.")
    voter = fetchone("SELECT is_eligible FROM voters WHERE voter_id=?", (voter_id.strip().lower(),))
    if not voter or not voter["is_eligible"]:
        raise ValueError("This account is not approved to vote in VoteChain. Contact the election administrator.")

    encrypted = encrypt_ballot(candidate_index, len(election["candidates"]))
    commitment = ballot_commitment(election_id, encrypted)
    nullifier = make_nullifier(election_id, voter_id, _nullifier_secret())

    # Persist a recoverable local intent before sending anything to the chain.
    # Reuse a prior FAILED row for this deterministic nullifier so a voter can
    # safely retry after an explicitly failed / never-submitted transaction.
    with connect() as conn:
        previous = conn.execute(
            "SELECT pending_id,status FROM pending_ballots WHERE election_id=? AND nullifier=?",
            (election_id, nullifier)
        ).fetchone()
        if previous and previous["status"] in ("PENDING", "REVIEW", "CONFIRMED"):
            raise ValueError("A ballot submission for this voter is already pending or confirmed.")
        if previous:
            pending_id = previous["pending_id"]
            conn.execute(
                "UPDATE pending_ballots SET voter_id=?,encrypted_values_json=?,commitment=?,tx_hash=NULL,status='PENDING',error_message='',updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                (voter_id.strip().lower(), json.dumps(encrypted), commitment, pending_id)
            )
        else:
            cur = conn.execute(
                "INSERT INTO pending_ballots(election_id,voter_id,encrypted_values_json,commitment,nullifier,status) VALUES(?,?,?,?,?,'PENDING')",
                (election_id, voter_id.strip().lower(), json.dumps(encrypted), commitment, nullifier)
            )
            pending_id = cur.lastrowid

    def remember_tx_hash(tx_hash):
        with connect() as conn:
            conn.execute("UPDATE pending_ballots SET tx_hash=?, updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                         (tx_hash, pending_id))

    tx_hash = None
    try:
        tx_hash = record_ballot(election_id, commitment, nullifier, on_submitted=remember_tx_hash)
        remember_tx_hash(tx_hash)
        _finalize_pending_ballot(pending_id)
    except Exception as exc:
        submitted_hash = getattr(exc, "tx_hash", None) or tx_hash
        with connect() as conn:
            row = conn.execute("SELECT tx_hash FROM pending_ballots WHERE pending_id=?", (pending_id,)).fetchone()
            saved_hash = (row["tx_hash"] if row else None) or submitted_hash
            state = "REVIEW" if saved_hash else "FAILED"
            conn.execute("UPDATE pending_ballots SET tx_hash=COALESCE(?,tx_hash),status=?,error_message=?,updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                         (submitted_hash, state, str(exc)[:1000], pending_id))
        if state == "REVIEW":
            raise ValueError(
                "The blockchain transaction was submitted or may be confirmed, but local confirmation needs reconciliation. "
                f"Do not vote again. Transaction: {saved_hash}"
            ) from exc
        raise ValueError(f"Ballot submission failed before a transaction hash was recorded: {exc}") from exc

    return {"commitment": commitment, "tx_hash": tx_hash}


def _finalize_pending_ballot(pending_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM pending_ballots WHERE pending_id=?", (pending_id,)).fetchone()
        if not row:
            raise ValueError("Pending ballot record was not found.")
        if row["status"] == "CONFIRMED":
            return
        if not row["tx_hash"]:
            raise ValueError("Cannot finalize a ballot without a transaction hash.")
        conn.execute(
            "INSERT OR IGNORE INTO used_voters(election_id,voter_id,nullifier) VALUES(?,?,?)",
            (row["election_id"], row["voter_id"], row["nullifier"])
        )
        conn.execute(
            "INSERT OR IGNORE INTO ballots(election_id,encrypted_values_json,commitment,nullifier,tx_hash) VALUES(?,?,?,?,?)",
            (row["election_id"], row["encrypted_values_json"], row["commitment"], row["nullifier"], row["tx_hash"])
        )
        conn.execute("UPDATE pending_ballots SET status='CONFIRMED', error_message='', updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                     (pending_id,))


def get_pending_ballots():
    rows = fetchall("SELECT pending_id,election_id,voter_id,commitment,nullifier,tx_hash,status,error_message,created_at,updated_at FROM pending_ballots WHERE status IN ('PENDING','REVIEW') ORDER BY created_at")
    return [dict(row) for row in rows]


def reconcile_pending_ballot(pending_id):
    row = fetchone("SELECT * FROM pending_ballots WHERE pending_id=?", (pending_id,))
    if not row:
        raise ValueError("Pending ballot record was not found.")
    if row["status"] == "CONFIRMED":
        return {"status": "CONFIRMED", "message": "Already reconciled."}
    if not row["tx_hash"]:
        with connect() as conn:
            conn.execute("UPDATE pending_ballots SET status='FAILED', error_message='No transaction hash was recorded; voter may retry.', updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                         (pending_id,))
        return {"status": "FAILED", "message": "No transaction hash exists. The voter can retry."}
    receipt = transaction_receipt_status(row["tx_hash"])
    if receipt is None:
        return {"status": "WAITING", "message": "Transaction receipt is not available yet. Retry reconciliation later."}
    if receipt["status"] == 1:
        _finalize_pending_ballot(pending_id)
        return {"status": "CONFIRMED", "message": f"Confirmed in block {receipt['block_number']}."}
    with connect() as conn:
        conn.execute("UPDATE pending_ballots SET status='FAILED', error_message='Blockchain receipt status was failed; voter may retry.', updated_at=CURRENT_TIMESTAMP WHERE pending_id=?",
                     (pending_id,))
    return {"status": "FAILED", "message": "Blockchain transaction failed. The voter may retry."}


def close_election(election_id):
    with connect() as conn:
        cur = conn.execute("UPDATE elections SET status='CLOSED' WHERE election_id=? AND status='OPEN'", (election_id,))
        if cur.rowcount != 1:
            raise ValueError("Election not found or already closed.")


def election_ballots(election_id):
    rows = fetchall("SELECT encrypted_values_json, commitment, nullifier, tx_hash, created_at FROM ballots WHERE election_id=? ORDER BY ballot_id", (election_id,))
    return [{
        "encrypted_values": json.loads(r["encrypted_values_json"]),
        "commitment": r["commitment"], "nullifier": r["nullifier"],
        "tx_hash": r["tx_hash"], "created_at": r["created_at"]
    } for r in rows]


def has_voted(election_id, voter_id):
    return fetchone(
        "SELECT 1 FROM used_voters WHERE election_id=? AND voter_id=? "
        "UNION ALL SELECT 1 FROM pending_ballots WHERE election_id=? AND voter_id=? AND status IN ('PENDING','REVIEW','CONFIRMED') LIMIT 1",
        (election_id, voter_id.strip().lower(), election_id, voter_id.strip().lower())
    ) is not None
