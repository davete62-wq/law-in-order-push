"""routes/settings.py — Club-wide settings management"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader

router = APIRouter()


class SettingsBody(BaseModel):
    club_name: Optional[str] = None
    school_name: Optional[str] = None
    motto: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    president_instagram: Optional[str] = None
    vp_instagram: Optional[str] = None
    recruitment_open: Optional[bool] = None
    delegate_capacity: Optional[int] = None
    mock_trial_time: Optional[str] = None


class AccessCodeBody(BaseModel):
    role: str   # 'delegate' | 'leader'
    code: str


@router.get("/")
def get_settings():
    """Public endpoint — returns club name, motto, mission, vision, instagram handles."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT club_name, school_name, motto, mission, vision, "
                "president_instagram, vp_instagram, recruitment_open, "
                "delegate_capacity, mock_trial_time FROM club_settings WHERE id=1"
            )
            return cur.fetchone()


@router.patch("/")
def update_settings(body: SettingsBody, user=Depends(get_current_user)):
    require_leader(user)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update."}

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values())

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE club_settings SET {set_clause} WHERE id=1", values)
        conn.commit()
    return {"message": "Settings updated."}


@router.patch("/access-codes")
def update_access_code(body: AccessCodeBody, user=Depends(get_current_user)):
    require_leader(user)
    if body.role not in ("delegate", "leader"):
        from fastapi import HTTPException
        raise HTTPException(400, "Role must be 'delegate' or 'leader'.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE access_codes SET code=%s, updated_at=NOW() WHERE role=%s",
                (body.code.strip(), body.role),
            )
        conn.commit()
    return {"message": "Access code updated."}
