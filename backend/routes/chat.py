"""routes/chat.py — Chat rooms and messages"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader

router = APIRouter()


class RoomBody(BaseModel):
    name: str
    member_ids: list[int] = []
    add_all_delegates: bool = False


class MessageBody(BaseModel):
    body: str


@router.get("/rooms")
def list_rooms(user=Depends(get_current_user)):
    """Return chat rooms the current user belongs to."""
    if user["role"] == "applicant":
        return []

    with get_conn() as conn:
        with conn.cursor() as cur:
            if user["role"] in ("president", "vice_president"):
                cur.execute("SELECT * FROM chat_rooms ORDER BY room_type, name")
            else:
                cur.execute(
                    """
                    SELECT DISTINCT cr.* FROM chat_rooms cr
                    LEFT JOIN chat_room_members crm ON crm.room_id = cr.id
                    WHERE cr.room_type = 'general' OR crm.user_id = %s
                    ORDER BY cr.room_type, cr.name
                    """,
                    (user["id"],),
                )
            return cur.fetchall()


@router.post("/rooms")
def create_room(body: RoomBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_rooms (name, room_type, created_by) VALUES (%s,'group',%s) RETURNING id",
                (body.name, user["id"]),
            )
            new_id = cur.fetchone()["id"]
            # Always add creator
            cur.execute(
                "INSERT INTO chat_room_members (room_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (new_id, user["id"]),
            )
            # Add all delegates if selected
            if body.add_all_delegates:
                cur.execute(
                    """
                    INSERT INTO chat_room_members (room_id, user_id)
                    SELECT %s, id FROM users
                    WHERE role IN ('delegate', 'staff', 'president', 'vice_president') AND status = 'active'
                    ON CONFLICT DO NOTHING
                    """,
                    (new_id,),
                )
            # Add specific members
            for uid in body.member_ids:
                cur.execute(
                    "INSERT INTO chat_room_members (room_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (new_id, uid),
                )
        conn.commit()
    return {"id": new_id}


@router.get("/rooms/{room_id}/members")
def get_room_members(room_id: int, user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.first_name, u.last_name, u.username, u.role
                FROM chat_room_members crm
                JOIN users u ON u.id = crm.user_id
                WHERE crm.room_id = %s
                ORDER BY u.first_name, u.last_name
                """,
                (room_id,),
            )
            return cur.fetchall()


@router.delete("/rooms/{room_id}")
def delete_room(room_id: int, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Cannot delete the permanent general chat
            cur.execute("SELECT room_type FROM chat_rooms WHERE id=%s", (room_id,))
            room = cur.fetchone()
            if not room:
                raise HTTPException(404, "Room not found.")
            if room["room_type"] == "general":
                raise HTTPException(400, "The general chat cannot be deleted.")
            cur.execute("DELETE FROM chat_rooms WHERE id=%s", (room_id,))
        conn.commit()
    return {"message": "Deleted."}


@router.post("/rooms/{room_id}/members/{uid}")
def add_member(room_id: int, uid: int, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_room_members (room_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (room_id, uid),
            )
        conn.commit()
    return {"message": "Added."}


@router.delete("/rooms/{room_id}/members/{uid}")
def remove_member(room_id: int, uid: int, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_room_members WHERE room_id=%s AND user_id=%s",
                (room_id, uid),
            )
        conn.commit()
    return {"message": "Removed."}


@router.get("/rooms/{room_id}/messages")
def get_messages(room_id: int, user=Depends(get_current_user)):
    """Return the last 100 messages in a room. User must be a member."""
    if user["role"] == "applicant":
        raise HTTPException(403, "Applicants do not have access to group chats.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify room exists
            cur.execute("SELECT room_type FROM chat_rooms WHERE id=%s", (room_id,))
            room = cur.fetchone()
            if not room:
                raise HTTPException(404, "Chat room not found.")

            # For group rooms, verify membership unless user is a leader
            if room["room_type"] != "general" and user["role"] not in ("president", "vice_president"):
                cur.execute(
                    "SELECT 1 FROM chat_room_members WHERE room_id=%s AND user_id=%s",
                    (room_id, user["id"]),
                )
                if not cur.fetchone():
                    raise HTTPException(403, "You are not a member of this chat room.")

            cur.execute(
                "SELECT m.id, m.body, m.sent_at, u.first_name, u.last_name, u.username "
                "FROM chat_messages m JOIN users u ON u.id = m.user_id "
                "WHERE m.room_id = %s ORDER BY m.sent_at DESC LIMIT 100",
                (room_id,),
            )
            msgs = cur.fetchall()
            return list(reversed(msgs))


@router.post("/rooms/{room_id}/messages")
def send_message(room_id: int, body: MessageBody, user=Depends(get_current_user)):
    if not body.body.strip():
        raise HTTPException(400, "Message cannot be empty.")

    if user["role"] == "applicant":
        raise HTTPException(403, "Applicants do not have access to group chats.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify room exists
            cur.execute("SELECT room_type FROM chat_rooms WHERE id=%s", (room_id,))
            room = cur.fetchone()
            if not room:
                raise HTTPException(404, "Chat room not found.")

            # For group rooms, verify membership unless user is a leader
            if room["room_type"] != "general" and user["role"] not in ("president", "vice_president"):
                cur.execute(
                    "SELECT 1 FROM chat_room_members WHERE room_id=%s AND user_id=%s",
                    (room_id, user["id"]),
                )
                if not cur.fetchone():
                    raise HTTPException(403, "You are not a member of this chat room.")

            cur.execute(
                "INSERT INTO chat_messages (room_id, user_id, body) VALUES (%s,%s,%s) RETURNING id, sent_at",
                (room_id, user["id"], body.body.strip()),
            )
            msg = cur.fetchone()
        conn.commit()
    return {"id": msg["id"], "sent_at": msg["sent_at"]}
