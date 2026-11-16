"""routes/certificates.py — Issue and view certificates"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_conn
from auth import get_current_user, require_leader

router = APIRouter()


class CertBody(BaseModel):
    user_id: int
    category: str
    title: Optional[str] = None
    notes: Optional[str] = None


@router.get("/my")
def my_certificates(user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.*, u.first_name AS issuer_first, u.last_name AS issuer_last "
                "FROM certificates c JOIN users u ON u.id = c.issued_by "
                "WHERE c.user_id = %s ORDER BY c.issued_at DESC",
                (user["id"],),
            )
            return cur.fetchall()


@router.get("/all")
def all_certificates(user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.*, u.first_name, u.last_name FROM certificates c "
                "JOIN users u ON u.id = c.user_id ORDER BY c.issued_at DESC"
            )
            return cur.fetchall()


@router.post("/")
def issue_certificate(body: CertBody, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO certificates (user_id, category, title, issued_by, notes) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (body.user_id, body.category, body.title, user["id"], body.notes),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()
    return {"id": new_id}


@router.delete("/{cert_id}")
def revoke_certificate(cert_id: int, user=Depends(get_current_user)):
    require_leader(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM certificates WHERE id=%s", (cert_id,))
        conn.commit()
    return {"message": "Certificate revoked."}
