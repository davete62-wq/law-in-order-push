"""routes/announcements.py — Create, list, edit, delete announcements"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_conn
from auth import get_current_user, require_leader_or_staff

router = APIRouter()


class AnnouncementBody(BaseModel):
    title: str
    body: str
    is_public: bool = False
    pinned: bool = False


@router.get("/public")
def public_announcements():
    """Public endpoint — returns only public announcements."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, body, pinned, created_at FROM announcements "
                "WHERE is_public = TRUE ORDER BY pinned DESC, created_at DESC"
            )
            return cur.fetchall()


@router.get("/")
def list_announcements(user=Depends(get_current_user)):
    """Member endpoint — returns all announcements (public and private)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT a.*, u.first_name, u.last_name FROM announcements a "
                "JOIN users u ON u.id = a.created_by "
                "ORDER BY pinned DESC, created_at DESC"
            )
            return cur.fetchall()


@router.post("/")
def create_announcement(body: AnnouncementBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_announcements")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO announcements (title, body, is_public, pinned, created_by) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (body.title, body.body, body.is_public, body.pinned, user["id"]),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": new_id}


@router.patch("/{ann_id}")
def update_announcement(ann_id: int, body: AnnouncementBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_announcements")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE announcements SET title=%s, body=%s, is_public=%s, pinned=%s "
                "WHERE id=%s",
                (body.title, body.body, body.is_public, body.pinned, ann_id),
            )
        conn.commit()
    return {"message": "Updated."}


@router.delete("/{ann_id}")
def delete_announcement(ann_id: int, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_announcements")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM announcements WHERE id=%s", (ann_id,))
        conn.commit()
    return {"message": "Deleted."}
