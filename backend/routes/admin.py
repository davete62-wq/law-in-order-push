"""routes/admin.py — Admin-only routes (audit log, stats, teams)"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from database import get_conn
from auth import get_current_user, require_leader

router = APIRouter()


class TeamBody(BaseModel):
    name: str
    description: str = ""
    member_ids: List[int] = []


@router.get("/audit-log")
def get_audit_log(user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT al.*, u.first_name, u.last_name FROM audit_log al "
                "LEFT JOIN users u ON u.id = al.actor_id "
                "ORDER BY al.created_at DESC LIMIT 200"
            )
            return cur.fetchall()


@router.get("/stats")
def get_stats(user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM users WHERE status='active'")
            total = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS delegates FROM users WHERE role='delegate' AND status='active'")
            delegates = cur.fetchone()["delegates"]
            cur.execute("SELECT COUNT(*) AS applicants FROM users WHERE role='applicant' AND status='active'")
            applicants = cur.fetchone()["applicants"]
            cur.execute("SELECT COUNT(*) AS pending FROM applications WHERE status='pending' OR status='submitted'")
            pending = cur.fetchone()["pending"]
            return {
                "total_active": total,
                "delegates": delegates,
                "applicants": applicants,
                "pending_applications": pending,
            }


@router.get("/teams")
def list_teams(user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM teams ORDER BY name")
            return cur.fetchall()


@router.post("/teams")
def create_team(body: TeamBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (name, description, created_by) VALUES (%s,%s,%s) RETURNING id",
                (body.name, body.description, user["id"]),
            )
            tid = cur.fetchone()["id"]
            for uid in body.member_ids:
                cur.execute(
                    "INSERT INTO team_members (team_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (tid, uid),
                )
        conn.commit()
    return {"id": tid}


@router.delete("/teams/{tid}")
def delete_team(tid: int, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM teams WHERE id=%s", (tid,))
        conn.commit()
    return {"message": "Team deleted."}
