"""Candidate profile and election information storage for VoteChain.

This module adds tables alongside the original schema. It never modifies
ballots, voter eligibility, candidate ordering, or blockchain transactions.
"""
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH, ROOT

IMAGE_DIR = ROOT / "data" / "candidate_images"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_candidate_profiles():
    """Create additive tables; safe to call each time the app starts."""
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS candidate_profiles (
            election_id TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            position TEXT NOT NULL DEFAULT '',
            department TEXT NOT NULL DEFAULT '',
            academic_year TEXT NOT NULL DEFAULT '',
            manifesto TEXT NOT NULL DEFAULT '',
            promises TEXT NOT NULL DEFAULT '',
            photo_path TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (election_id, candidate_name)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS election_details (
            election_id TEXT PRIMARY KEY,
            position_title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (election_id) REFERENCES elections(election_id)
        )""")


def _safe_photo_path(relative_path):
    if not relative_path:
        return ""
    candidate = (ROOT / relative_path).resolve()
    image_root = IMAGE_DIR.resolve()
    if image_root not in candidate.parents or not candidate.is_file():
        return ""
    return str(candidate)


def get_candidate_profile(election_id, candidate_name):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM candidate_profiles WHERE election_id=? AND candidate_name=?",
            (election_id, candidate_name),
        ).fetchone()
    if row is None:
        return {"position": "", "department": "", "academic_year": "",
                "manifesto": "", "promises": "", "photo_path": ""}
    profile = dict(row)
    profile["photo_path"] = _safe_photo_path(profile.get("photo_path", ""))
    return profile


def save_candidate_profile(election_id, candidate_name, position="", department="",
                           academic_year="", manifesto="", promises="",
                           photo_bytes=None, photo_extension=None):
    if not election_id or not candidate_name:
        raise ValueError("Election and candidate are required.")
    new_photo_path = ""
    if photo_bytes:
        extension = (photo_extension or "").lower()
        if extension and not extension.startswith("."):
            extension = "." + extension
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Upload a PNG, JPG, JPEG or WEBP image.")
        if len(photo_bytes) > MAX_IMAGE_SIZE:
            raise ValueError("Candidate photo must be 5 MB or smaller.")
        # Check file signatures rather than trusting the filename extension.
        signatures = {
            ".jpg": photo_bytes.startswith(b"\xff\xd8\xff"),
            ".jpeg": photo_bytes.startswith(b"\xff\xd8\xff"),
            ".png": photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
            ".webp": len(photo_bytes) >= 12 and photo_bytes[:4] == b"RIFF" and photo_bytes[8:12] == b"WEBP",
        }
        if not signatures.get(extension, False):
            raise ValueError("The uploaded file content does not match its image extension.")
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(f"{election_id}:{candidate_name}".encode() + photo_bytes).hexdigest()[:24]
        filename = f"{digest}{extension}"
        (IMAGE_DIR / filename).write_bytes(photo_bytes)
        new_photo_path = str((IMAGE_DIR / filename).relative_to(ROOT))

    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO candidate_profiles
            (election_id,candidate_name,position,department,academic_year,manifesto,promises,photo_path,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(election_id,candidate_name) DO UPDATE SET
                position=excluded.position, department=excluded.department,
                academic_year=excluded.academic_year, manifesto=excluded.manifesto,
                promises=excluded.promises,
                photo_path=CASE WHEN excluded.photo_path='' THEN candidate_profiles.photo_path ELSE excluded.photo_path END,
                updated_at=excluded.updated_at""",
            (election_id, candidate_name, position.strip(), department.strip(), academic_year.strip(),
             manifesto.strip(), promises.strip(), new_photo_path, now))
    return True


def get_election_details(election_id):
    with _connect() as conn:
        row = conn.execute("SELECT position_title, description FROM election_details WHERE election_id=?",
                           (election_id,)).fetchone()
    return dict(row) if row else {"position_title": "", "description": ""}


def save_election_details(election_id, position_title="", description=""):
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        exists = conn.execute("SELECT 1 FROM elections WHERE election_id=?", (election_id,)).fetchone()
        if not exists:
            raise ValueError("Election not found.")
        conn.execute("""INSERT INTO election_details(election_id,position_title,description,updated_at)
            VALUES(?,?,?,?) ON CONFLICT(election_id) DO UPDATE SET
            position_title=excluded.position_title, description=excluded.description,
            updated_at=excluded.updated_at""",
            (election_id, position_title.strip(), description.strip(), now))
    return True
