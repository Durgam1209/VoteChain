import bcrypt
from database.db import connect


def create_user(voter_id: str, display_name: str, password: str, is_admin=False, eligible=True):
    voter_id = voter_id.strip().lower()
    if not voter_id or not display_name.strip() or len(password) < 8:
        raise ValueError("Enter a voter ID, display name and password of at least 8 characters.")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO voters(voter_id, display_name, password_hash, is_admin, is_eligible) VALUES(?,?,?,?,?)",
                (voter_id, display_name.strip(), password_hash, int(is_admin), int(bool(eligible) or bool(is_admin)))
            )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise ValueError("That voter ID is already registered.") from exc
        raise


def authenticate(voter_id: str, password: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT voter_id, display_name, password_hash, is_admin, is_eligible FROM voters WHERE voter_id=?",
            (voter_id.strip().lower(),)
        ).fetchone()
    if not row or not bcrypt.checkpw(password.encode(), row["password_hash"]):
        return None
    if not row["is_admin"] and not row["is_eligible"]:
        return {"pending_approval": True}
    return {"voter_id": row["voter_id"], "display_name": row["display_name"],
            "is_admin": bool(row["is_admin"]), "is_eligible": bool(row["is_eligible"])}


def list_voters():
    with connect() as conn:
        return conn.execute(
            "SELECT voter_id, display_name, is_admin, is_eligible FROM voters ORDER BY is_admin DESC, voter_id"
        ).fetchall()


def set_voter_eligibility(voter_id: str, eligible: bool):
    with connect() as conn:
        cur = conn.execute(
            "UPDATE voters SET is_eligible=? WHERE voter_id=? AND is_admin=0",
            (int(bool(eligible)), voter_id.strip().lower())
        )
        if cur.rowcount != 1:
            raise ValueError("Voter not found, or administrator eligibility cannot be changed here.")
