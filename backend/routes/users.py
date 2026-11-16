"""routes/users.py — Member management and applications"""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader, require_leader_or_staff
from routes.case_files import store_file_bytes, ALLOWED_EXTS, ALLOWED_MIME, MAX_MB

router = APIRouter()


class StatusBody(BaseModel):
    status: str  # 'active' | 'suspended' | 'deleted'


class PermissionsBody(BaseModel):
    can_review_applications: bool = False
    can_review_essays: bool = False
    can_manage_assignments: bool = False
    can_manage_events: bool = False
    can_manage_announcements: bool = False
    can_manage_case_files: bool = False
    can_manage_chats: bool = False
    can_manage_points: bool = False
    can_manage_participation: bool = False
    can_manage_rules: bool = False


class ApplicationDecisionBody(BaseModel):
    decision: str         # 'pass' | 'fail'
    reviewer_notes: Optional[str] = None


@router.get("/")
def list_members(user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, member_number, username, first_name, last_name, grade, role, status, created_at "
                "FROM users WHERE status != 'deleted' ORDER BY member_number ASC"
            )
            return cur.fetchall()


@router.get("/applicants")
def list_applicants(user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_review_applications")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.member_number, u.first_name, u.last_name, u.grade, "
                "a.status AS app_status, a.submitted_at, a.id AS application_id, "
                "a.essay_filename, a.essay_url, a.reviewer_notes "
                "FROM users u JOIN applications a ON a.user_id = u.id "
                "WHERE u.role = 'applicant' AND u.status = 'active' ORDER BY u.created_at ASC"
            )
            return cur.fetchall()


@router.get("/application/{app_id}")
def get_application(app_id: int, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_review_essays")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT a.*, u.first_name, u.last_name, u.grade, u.username "
                "FROM applications a JOIN users u ON u.id = a.user_id WHERE a.id = %s",
                (app_id,),
            )
            return cur.fetchone()


@router.post("/application/{app_id}/decide")
def decide_application(app_id: int, body: ApplicationDecisionBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_review_applications")
    if body.decision not in ("pass", "fail"):
        raise HTTPException(400, "Decision must be 'pass' or 'fail'.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM applications WHERE id=%s", (app_id,))
            app = cur.fetchone()
            if not app:
                raise HTTPException(404, "Application not found.")

            uid = app["user_id"]
            cur.execute(
                "UPDATE applications SET status=%s, reviewed_by=%s, reviewed_at=NOW(), reviewer_notes=%s WHERE id=%s",
                (body.decision, user["id"], body.reviewer_notes, app_id),
            )

            if body.decision == "pass":
                # Promote the applicant to delegate
                cur.execute("UPDATE users SET role='delegate' WHERE id=%s", (uid,))

            # Audit log
            cur.execute(
                "INSERT INTO audit_log (actor_id, action, target_id, detail) VALUES (%s,%s,%s,%s)",
                (user["id"], f"application_{body.decision}", uid, body.reviewer_notes),
            )
        conn.commit()
    return {"message": f"Application marked as {body.decision}."}


@router.get("/my-application")
def my_application(user=Depends(get_current_user)):
    """Applicants check their own application status."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, submitted_at, essay_filename FROM applications WHERE user_id=%s",
                (user["id"],),
            )
            return cur.fetchone()


@router.post("/my-application/submit-essay")
async def submit_essay(file: UploadFile = File(...), user=Depends(get_current_user)):
    """
    Applicants upload their single required essay file (PDF or DOCX).
    Resubmission is strictly blocked as per specifications.
    """
    if user["role"] != "applicant":
        raise HTTPException(400, "Only applicants can submit an admission essay.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS and file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, "Only PDF and DOCX files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_MB} MB limit.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, status FROM applications WHERE user_id = %s", (user["id"],))
            app = cur.fetchone()
            if not app:
                cur.execute("INSERT INTO applications (user_id) VALUES (%s) RETURNING id, status", (user["id"],))
                app = cur.fetchone()

            if app["status"] in ("submitted", "pass", "fail"):
                raise HTTPException(400, "You have already submitted an essay. Resubmission is not permitted.")

            essay_url = await store_file_bytes(file.filename or "essay.pdf", contents)

            cur.execute(
                """
                UPDATE applications
                SET essay_filename = %s, essay_url = %s, essay_mime = %s,
                    submitted_at = NOW(), status = 'submitted'
                WHERE user_id = %s
                """,
                (file.filename, essay_url, file.content_type, user["id"]),
            )
            # Also record in case_files
            cur.execute(
                """
                INSERT INTO case_files (filename, file_url, mime_type, category, description, uploaded_by)
                VALUES (%s, %s, %s, 'case', 'Applicant admission essay', %s)
                """,
                (file.filename, essay_url, file.content_type, user["id"]),
            )
        conn.commit()

    return {"message": "Essay submitted successfully.", "essay_url": essay_url}


@router.patch("/{uid}/status")
def change_status(uid: int, body: StatusBody, user=Depends(get_current_user)):
    require_leader(user)
    if body.status not in ("active", "suspended", "deleted"):
        raise HTTPException(400, "Invalid status.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status=%s WHERE id=%s", (body.status, uid))
            cur.execute(
                "INSERT INTO audit_log (actor_id, action, target_id) VALUES (%s,%s,%s)",
                (user["id"], f"set_status_{body.status}", uid),
            )
        conn.commit()
    return {"message": f"User status set to {body.status}."}


@router.patch("/{uid}/permissions")
def set_permissions(uid: int, body: PermissionsBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify target is staff
            cur.execute("SELECT role FROM users WHERE id=%s", (uid,))
            target = cur.fetchone()
            if not target or target["role"] != "staff":
                raise HTTPException(400, "Target user must be a staff member.")

            cur.execute(
                """
                INSERT INTO staff_permissions (user_id,
                    can_review_applications, can_review_essays,
                    can_manage_assignments, can_manage_events,
                    can_manage_announcements, can_manage_case_files,
                    can_manage_chats, can_manage_points,
                    can_manage_participation, can_manage_rules)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id) DO UPDATE SET
                    can_review_applications=EXCLUDED.can_review_applications,
                    can_review_essays=EXCLUDED.can_review_essays,
                    can_manage_assignments=EXCLUDED.can_manage_assignments,
                    can_manage_events=EXCLUDED.can_manage_events,
                    can_manage_announcements=EXCLUDED.can_manage_announcements,
                    can_manage_case_files=EXCLUDED.can_manage_case_files,
                    can_manage_chats=EXCLUDED.can_manage_chats,
                    can_manage_points=EXCLUDED.can_manage_points,
                    can_manage_participation=EXCLUDED.can_manage_participation,
                    can_manage_rules=EXCLUDED.can_manage_rules
                """,
                (uid,
                 body.can_review_applications, body.can_review_essays,
                 body.can_manage_assignments, body.can_manage_events,
                 body.can_manage_announcements, body.can_manage_case_files,
                 body.can_manage_chats, body.can_manage_points,
                 body.can_manage_participation, body.can_manage_rules),
            )
        conn.commit()
    return {"message": "Permissions updated."}


@router.patch("/{uid}/role")
def change_role(uid: int, new_role: str, user=Depends(get_current_user)):
    """Promote a delegate to staff, etc. Only leaders can do this."""
    require_leader(user)
    allowed = ("applicant", "delegate", "staff", "president", "vice_president")
    if new_role not in allowed:
        raise HTTPException(400, "Invalid role.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, uid))
            if new_role == "staff":
                # Ensure a permissions row exists
                cur.execute(
                    "INSERT INTO staff_permissions (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (uid,),
                )
            cur.execute(
                "INSERT INTO audit_log (actor_id, action, target_id, detail) VALUES (%s,%s,%s,%s)",
                (user["id"], "change_role", uid, new_role),
            )
        conn.commit()
    return {"message": f"Role changed to {new_role}."}
