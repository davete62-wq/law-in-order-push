"""
auth.py — Authentication helpers
=================================
Handles password hashing, session tokens, and the
get_current_user dependency used by every protected route.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, HTTPException, status
from dotenv import load_dotenv

from database import get_conn

load_dotenv()

SESSION_HOURS = int(os.getenv("SESSION_HOURS", "24"))


# ── Password hashing ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Session management ────────────────────────────────────────────

def create_session(user_id: int) -> str:
    """Create a session token in the database and return it."""
    token = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (token, user_id, expires),
            )
        conn.commit()
    return token


def delete_session(token: str):
    """Delete a session (logout)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()


def get_session_user(token: str) -> dict | None:
    """
    Look up the session token and return the full user row if valid.
    Returns None if the token is missing, expired, or the user is suspended/deleted.
    """
    if not token:
        return None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.*
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = %s
                  AND s.expires_at > NOW()
                  AND u.status = 'active'
                """,
                (token,),
            )
            return cur.fetchone()


# ── FastAPI dependency ────────────────────────────────────────────

def get_current_user(session: str | None = Cookie(default=None)) -> dict:
    """
    FastAPI dependency. Use as:  user = Depends(get_current_user)
    Raises HTTP 401 if not authenticated.
    """
    user = get_session_user(session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_leader(user: dict):
    """Raise 403 if user is not president or vice president."""
    if user["role"] not in ("president", "vice_president"):
        raise HTTPException(status_code=403, detail="Leadership access required")


def require_leader_or_staff(user: dict, permission_flag: str | None = None):
    """
    Raise 403 unless:
    - user is president/vice president, OR
    - user is staff AND has the given permission flag set to True.
    """
    if user["role"] in ("president", "vice_president"):
        return
    if user["role"] == "staff" and permission_flag:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {permission_flag} FROM staff_permissions WHERE user_id = %s",
                    (user["id"],),
                )
                row = cur.fetchone()
                if row and row[permission_flag]:
                    return
    raise HTTPException(status_code=403, detail="Insufficient permissions")
