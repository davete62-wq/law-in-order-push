"""routes/auth.py — Registration and login/logout"""

import os
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_conn
from auth import hash_password, verify_password, create_session, delete_session
from limiter import limiter

router = APIRouter()


class RegisterBody(BaseModel):
    username: str
    first_name: str
    last_name: str
    grade: int
    password: str
    access_code: str


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
@limiter.limit("10/minute")
def register(body: RegisterBody, request: Request, response: Response):
    """
    Public endpoint. Students register themselves here.
    The access code determines whether they become an applicant or leader.
    No email or phone required.
    """
    if body.grade not in (9, 10, 11, 12):
        raise HTTPException(400, "Grade must be 9, 10, 11, or 12.")

    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Validate access code
            cur.execute(
                "SELECT role, active FROM access_codes WHERE code = %s",
                (body.access_code.strip(),),
            )
            code_row = cur.fetchone()
            if not code_row or not code_row["active"]:
                raise HTTPException(400, "Invalid or inactive access code.")

            # Map code role to user role
            role_map = {
                "delegate": "applicant",   # Delegates start as applicants
                "leader":   "president",   # Leader code — first use gets president
            }
            user_role = role_map.get(code_row["role"], "applicant")

            # If 'leader' code — first user gets president, second gets vice_president
            if code_row["role"] == "leader":
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM users WHERE role IN ('president','vice_president')"
                )
                cnt = cur.fetchone()["cnt"]
                if cnt == 0:
                    user_role = "president"
                elif cnt == 1:
                    user_role = "vice_president"
                else:
                    raise HTTPException(400, "Leadership positions are already filled.")

            # Check username uniqueness
            cur.execute("SELECT id FROM users WHERE username = %s", (body.username.strip(),))
            if cur.fetchone():
                raise HTTPException(400, "Username already taken.")

            # Check recruitment for delegates
            if user_role == "applicant":
                cur.execute("SELECT recruitment_open FROM club_settings WHERE id = 1")
                settings = cur.fetchone()
                if settings and not settings["recruitment_open"]:
                    raise HTTPException(400, "Recruitment is currently closed.")

            # Create the user
            pw_hash = hash_password(body.password)
            cur.execute(
                """
                INSERT INTO users (username, first_name, last_name, grade, role, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, member_number, role
                """,
                (
                    body.username.strip(),
                    body.first_name.strip(),
                    body.last_name.strip(),
                    body.grade,
                    user_role,
                    pw_hash,
                ),
            )
            new_user = cur.fetchone()
            user_id = new_user["id"]

            # Create application row for applicants
            if user_role == "applicant":
                cur.execute(
                    "INSERT INTO applications (user_id) VALUES (%s)", (user_id,)
                )

            # Create staff_permissions row for staff (not needed here but on promotion)
            # Create points row for all users
            cur.execute("INSERT INTO points (user_id) VALUES (%s)", (user_id,))

            # Add to general chat room
            cur.execute("SELECT id FROM chat_rooms WHERE room_type = 'general' LIMIT 1")
            gen_room = cur.fetchone()
            if gen_room:
                cur.execute(
                    "INSERT INTO chat_room_members (room_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (gen_room["id"], user_id),
                )

        conn.commit()

    # Log the user in immediately after registration
    token = create_session(user_id)
    response.set_cookie(
        "session", token,
        httponly=True, samesite="none", secure=True,
        path="/",
        max_age=86400 * 7,
    )
    return {
        "message": "Account created successfully.",
        "member_number": f"#{new_user['member_number']:03d}",
        "role": user_role,
    }


@router.post("/login")
@limiter.limit("15/minute")
def login(body: LoginBody, request: Request, response: Response):
    """Login with username and password."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s AND status != 'deleted'",
                (body.username.strip(),),
            )
            user = cur.fetchone()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password.")

    if user["status"] == "suspended":
        raise HTTPException(403, "Your account has been suspended. Contact the club leadership.")

    token = create_session(user["id"])
    response.set_cookie(
        "session", token,
        httponly=True, samesite="none", secure=True,
        path="/",
        max_age=86400 * 7,
    )
    return {
        "id": user["id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "role": user["role"],
        "member_number": f"#{user['member_number']:03d}",
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    """
    Destroys the session in PostgreSQL and wipes the session cookie from the browser.
    Ensures no previous user info remains accessible.
    """
    token = request.cookies.get("session")
    if token:
        delete_session(token)
    response.delete_cookie(
        "session",
        path="/",
        samesite="none",
        secure=True,
    )
    return {"message": "Logged out and session destroyed."}


@router.get("/me")
def me(request: Request):
    """Return the currently logged-in user's info."""
    from auth import get_session_user
    token = request.cookies.get("session")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "Not authenticated.")
    return {
        "id": user["id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "role": user["role"],
        "grade": user["grade"],
        "member_number": f"#{user['member_number']:03d}",
        "profile_pic_url": user["profile_pic_url"],
        "status": user["status"],
    }
