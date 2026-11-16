"""routes/case_files.py — File upload, retrieval and storage with local fallback"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from dotenv import load_dotenv
from database import get_conn
from auth import get_current_user, require_leader_or_staff

load_dotenv()

# Cloudinary optional setup
CLOUDINARY_AVAILABLE = False
try:
    import cloudinary
    import cloudinary.uploader
    if os.getenv("CLOUDINARY_CLOUD_NAME") and os.getenv("CLOUDINARY_API_KEY"):
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True,
        )
        CLOUDINARY_AVAILABLE = True
except ImportError:
    pass

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
ALLOWED_EXTS = {".pdf", ".docx", ".doc"}
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

router = APIRouter()


async def store_file_bytes(filename: str, contents: bytes) -> str:
    """Store file either in Cloudinary or locally on disk."""
    if CLOUDINARY_AVAILABLE:
        result = cloudinary.uploader.upload(
            contents,
            resource_type="raw",
            folder="law_in_order",
            use_filename=True,
            unique_filename=True,
        )
        return result["secure_url"]
    else:
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        dest = UPLOAD_DIR / safe_name
        dest.write_bytes(contents)
        return f"/api/files/download/{safe_name}"


@router.get("/download/{filename}")
def download_local_file(filename: str, user=Depends(get_current_user)):
    """Serve locally stored uploads to authenticated users."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found.")
    display_name = filename.split("_", 1)[-1] if "_" in filename else filename
    return FileResponse(file_path, filename=display_name)


@router.get("/")
def list_files(user=Depends(get_current_user)):
    """Return files the current user is allowed to see."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if user["role"] in ("president", "vice_president", "staff", "delegate"):
                cur.execute("SELECT * FROM case_files ORDER BY uploaded_at DESC")
            else:
                # Applicants see general and constitution/rules files only
                cur.execute(
                    "SELECT * FROM case_files WHERE category IN ('general','constitution','rules') "
                    "ORDER BY uploaded_at DESC"
                )
            return cur.fetchall()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: Optional[str] = Form(None),
    mock_trial_id: Optional[int] = Form(None),
    assignment_id: Optional[int] = Form(None),
    user=Depends(get_current_user),
):
    require_leader_or_staff(user, "can_manage_case_files")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS and file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, "Only PDF and DOCX files are accepted.")

    contents = await file.read()
    if len(contents) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_MB} MB limit.")

    file_url = await store_file_bytes(file.filename or "document.pdf", contents)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO case_files (filename, file_url, mime_type, category, mock_trial_id, assignment_id, description, uploaded_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                (file.filename, file_url, file.content_type, category,
                 mock_trial_id, assignment_id, description, user["id"]),
            )
            new_id = cur.fetchone()["id"]
        conn.commit()

    return {"id": new_id, "url": file_url}


@router.delete("/{file_id}")
def delete_file(file_id: int, user=Depends(get_current_user)):
    require_leader_or_staff(user, "can_manage_case_files")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM case_files WHERE id=%s", (file_id,))
        conn.commit()
    return {"message": "Deleted."}
