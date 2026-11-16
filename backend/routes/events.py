"""routes/events.py — Club events management"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader_or_staff

router = APIRouter()


class EventBody(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: str         # ISO date string: 'YYYY-MM-DD'
    event_time: Optional[str] = None
    location: Optional[str] = None
    is_public: bool = False


@router.get("/public")
def public_events():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description, event_date, event_time, location "
                "FROM events WHERE is_public=TRUE AND event_date >= CURRENT_DATE "
                "ORDER BY event_date ASC"
            )
            return cur.fetchall()


@router.get("/")
def list_events(user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT e.*, u.first_name, u.last_name FROM events e "
                "JOIN users u ON u.id = e.created_by ORDER BY event_date ASC"
            )
            return cur.fetchall()


@router.post("/")
def create_event(body: EventBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_events")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO events (title, description, event_date, event_time, location, is_public, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.title, body.description, body.event_date, body.event_time,
                 body.location, body.is_public, user["id"]),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": new_id}


@router.patch("/{event_id}")
def update_event(event_id: int, body: EventBody, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_events")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE events SET title=%s, description=%s, event_date=%s, event_time=%s, "
                "location=%s, is_public=%s WHERE id=%s",
                (body.title, body.description, body.event_date, body.event_time,
                 body.location, body.is_public, event_id),
            )
        conn.commit()
    return {"message": "Updated."}


@router.delete("/{event_id}")
def delete_event(event_id: int, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_events")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id=%s", (event_id,))
        conn.commit()
    return {"message": "Deleted."}
