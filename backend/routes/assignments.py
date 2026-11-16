"""routes/assignments.py — Assignment creation and submission tracking"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_conn
from auth import get_current_user, require_leader_or_staff

router = APIRouter()


class AssignmentBody(BaseModel):
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    deadline: Optional[str] = None      # ISO datetime string
    user_ids: List[int] = []
    team_ids: List[int] = []


class SubmissionBody(BaseModel):
    assignment_id: int
    status: str  # 'submitted' | 'approved' | 'rejected'
    notes: Optional[str] = None


@router.get("/my")
def my_assignments(user=Depends(get_current_user)):
    """Return assignments assigned to the current user (directly or via team)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT a.* FROM assignments a
                LEFT JOIN assignment_assignees aa ON aa.assignment_id = a.id
                LEFT JOIN assignment_teams at2 ON at2.assignment_id = a.id
                LEFT JOIN team_members tm ON tm.team_id = at2.team_id
                WHERE aa.user_id = %s OR tm.user_id = %s
                ORDER BY a.deadline ASC NULLS LAST
                """,
                (user["id"], user["id"]),
            )
            return cur.fetchall()


@router.get("/")
def list_assignments(user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_assignments")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM assignments ORDER BY created_at DESC")
            return cur.fetchall()


@router.post("/")
def create_assignment(body: AssignmentBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_assignments")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO assignments (title, description, instructions, deadline, created_by) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (body.title, body.description, body.instructions, body.deadline, user["id"]),
            )
            asgn_id = cur.fetchone()["id"]

            for uid in body.user_ids:
                cur.execute(
                    "INSERT INTO assignment_assignees (assignment_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (asgn_id, uid),
                )
                cur.execute(
                    "INSERT INTO assignment_submissions (assignment_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (asgn_id, uid),
                )

            for tid in body.team_ids:
                cur.execute(
                    "INSERT INTO assignment_teams (assignment_id, team_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (asgn_id, tid),
                )

        conn.commit()
    return {"id": asgn_id}


@router.patch("/submissions/{asgn_id}/{uid}")
def update_submission(asgn_id: int, uid: int, body: SubmissionBody, user=Depends(get_current_user)):
    """Mark a submission as submitted (by delegate) or approved/rejected (by staff/leader)."""
    # Delegates can only mark their own as 'submitted'
    if user["role"] in ("delegate", "applicant"):
        if uid != user["id"]:
            raise HTTPException(403, "Cannot update another member's submission.")
        if body.status != "submitted":
            raise HTTPException(403, "Delegates can only mark their own work as submitted.")
    else:
        require_leader_or_staff(user, "can_manage_assignments")

    with get_conn() as conn:
        with conn.cursor() as cur:
            from datetime import datetime, timezone
            submitted_at = datetime.now(timezone.utc) if body.status == "submitted" else None
            cur.execute(
                "UPDATE assignment_submissions SET status=%s, notes=%s, submitted_at=%s "
                "WHERE assignment_id=%s AND user_id=%s",
                (body.status, body.notes, submitted_at, asgn_id, uid),
            )
        conn.commit()
    return {"message": "Updated."}
