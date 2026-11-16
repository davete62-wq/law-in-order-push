"""routes/points.py — Points and participation rankings"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader_or_staff

router = APIRouter()


class PointBody(BaseModel):
    user_id: int
    delta: int   # positive to add, negative to deduct
    reason: Optional[str] = None


@router.get("/rankings")
def rankings(user=Depends(get_current_user)):
    """Public leaderboard visible to all logged-in members."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.first_name, u.last_name, u.member_number, p.total "
                "FROM points p JOIN users u ON u.id = p.user_id "
                "WHERE u.role = 'delegate' AND u.status = 'active' "
                "ORDER BY p.total DESC"
            )
            return cur.fetchall()


@router.get("/my")
def my_points(user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT total FROM points WHERE user_id = %s", (user["id"],))
            row = cur.fetchone()
            return {"total": row["total"] if row else 0}


@router.get("/history/{uid}")
def point_history(uid: int, user=Depends(get_current_user)):
    # Only the user themselves or a leader/authorized staff can view history
    if user["id"] != uid:
        require_leader_or_staff(user, "can_manage_points")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pal.delta, pal.reason, pal.created_at, u.first_name, u.last_name "
                "FROM point_audit_log pal JOIN users u ON u.id = pal.changed_by "
                "WHERE pal.user_id = %s ORDER BY pal.created_at DESC",
                (uid,),
            )
            return cur.fetchall()


@router.post("/award")
def award_points(body: PointBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_points")
    if body.delta == 0:
        raise HTTPException(400, "Delta cannot be zero.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Update or insert points row
            cur.execute(
                "INSERT INTO points (user_id, total) VALUES (%s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET total = points.total + EXCLUDED.total",
                (body.user_id, body.delta),
            )
            # Record the change
            cur.execute(
                "INSERT INTO point_audit_log (user_id, changed_by, delta, reason) VALUES (%s,%s,%s,%s)",
                (body.user_id, user["id"], body.delta, body.reason),
            )
        conn.commit()
    return {"message": "Points updated."}
