"""routes/mock_trials.py — Mock trial management"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader

router = APIRouter()


class TrialBody(BaseModel):
    title: str
    trial_type: str = "monthly"
    trial_date: str
    trial_time: Optional[str] = None
    case_topic: Optional[str] = None
    instructions: Optional[str] = None


class RoleBody(BaseModel):
    mock_trial_id: int
    user_id: int
    role_name: str


@router.get("/")
def list_trials(user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM mock_trials ORDER BY trial_date ASC")
            return cur.fetchall()


@router.post("/")
def create_trial(body: TrialBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mock_trials (title, trial_type, trial_date, trial_time, case_topic, instructions, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.title, body.trial_type, body.trial_date, body.trial_time,
                 body.case_topic, body.instructions, user["id"]),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": new_id}


@router.patch("/{trial_id}")
def update_trial(trial_id: int, body: TrialBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE mock_trials SET title=%s, trial_type=%s, trial_date=%s, trial_time=%s, "
                "case_topic=%s, instructions=%s WHERE id=%s",
                (body.title, body.trial_type, body.trial_date, body.trial_time,
                 body.case_topic, body.instructions, trial_id),
            )
        conn.commit()
    return {"message": "Updated."}


@router.post("/roles")
def assign_role(body: RoleBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mock_trial_roles (mock_trial_id, user_id, role_name) "
                "VALUES (%s,%s,%s) ON CONFLICT (mock_trial_id, user_id) "
                "DO UPDATE SET role_name=EXCLUDED.role_name",
                (body.mock_trial_id, body.user_id, body.role_name),
            )
        conn.commit()
    return {"message": "Role assigned."}


@router.get("/{trial_id}/roles")
def get_trial_roles(trial_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mtr.role_name, u.first_name, u.last_name, u.username "
                "FROM mock_trial_roles mtr JOIN users u ON u.id = mtr.user_id "
                "WHERE mtr.mock_trial_id = %s",
                (trial_id,),
            )
            return cur.fetchall()
