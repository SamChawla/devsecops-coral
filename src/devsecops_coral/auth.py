"""Lightweight organization-scoped authentication for the dashboard.

Uses only the standard library: a small SQLite database for orgs/users/sessions
and ``hashlib.pbkdf2_hmac`` for password hashing. There are no external auth
dependencies and no secrets stored in code. Sessions are opaque random tokens
carried in an httpOnly cookie (set by the API layer), never in localStorage.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from devsecops_coral.config import AUTH_DB_PATH, SESSION_TTL_HOURS

_PBKDF2_ITERATIONS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """Raised for recoverable authentication problems (bad input, conflicts)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _connect() -> sqlite3.Connection:
    """Open a SQLite connection, creating the parent directory if needed."""
    db_path = Path(AUTH_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the auth tables if they do not yet exist."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orgs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id        INTEGER NOT NULL REFERENCES orgs(id),
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'member',
                created_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )


def reset_db() -> None:
    """Delete all auth data (orgs, users, sessions) and recreate empty tables.

    Used by ``devsecops-coral reset`` to start a clean demo. Run with the server
    stopped so no request holds the database file open.
    """
    db_path = Path(AUTH_DB_PATH)
    if db_path.exists():
        db_path.unlink()
    init_db()


def _hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
    )
    return derived.hex()


def _public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "email": row["email"], "role": row["role"]}


def _public_org(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "name": row["name"]}


def signup(email: str, password: str, org_name: str) -> dict[str, Any]:
    """Create an organization and its first (owner) user.

    Args:
        email: New user's email address.
        password: Plaintext password (min 8 chars).
        org_name: Display name for the new organization.

    Returns:
        ``{"user": {...}, "org": {...}}`` describing the created records.

    Raises:
        AuthError: On invalid input or if the email is already registered.
    """
    email = (email or "").strip().lower()
    org_name = (org_name or "").strip()
    if not _EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.")
    if len(password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")
    if not org_name:
        raise AuthError("Organization name is required.")

    salt = secrets.token_hex(16)
    created = _now().isoformat()
    with _connect() as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise AuthError("An account with that email already exists.")
        org_cur = conn.execute(
            "INSERT INTO orgs (name, created_at) VALUES (?, ?)", (org_name, created)
        )
        org_id = org_cur.lastrowid
        conn.execute(
            """
            INSERT INTO users (org_id, email, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, 'owner', ?)
            """,
            (org_id, email, _hash_password(password, salt), salt, created),
        )
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (org_id,)).fetchone()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return {"user": _public_user(user), "org": _public_org(org)}


def authenticate(email: str, password: str) -> dict[str, Any]:
    """Verify credentials and return the user/org payload.

    Raises:
        AuthError: If the email is unknown or the password does not match.
    """
    email = (email or "").strip().lower()
    with _connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or _hash_password(password, user["salt"]) != user["password_hash"]:
            raise AuthError("Incorrect email or password.")
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
    return {"user": _public_user(user), "org": _public_org(org)}


def create_session(user_id: int) -> str:
    """Create a session token for ``user_id`` and return it."""
    token = secrets.token_urlsafe(32)
    now = _now()
    expires = now + timedelta(hours=SESSION_TTL_HOURS)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), expires.isoformat()),
        )
    return token


def session_user(token: str | None) -> dict[str, Any] | None:
    """Return ``{"user": ..., "org": ...}`` for a valid session, else ``None``.

    Expired sessions are deleted and treated as invalid.
    """
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        try:
            expires = datetime.fromisoformat(row["expires_at"])
        except ValueError:
            expires = _now() - timedelta(seconds=1)
        if expires < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        user = conn.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
        if user is None:
            return None
        org = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
    return {"user": _public_user(user), "org": _public_org(org)}


def delete_session(token: str | None) -> None:
    """Remove a session token (logout). No-op when token is falsy."""
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
