"""
main.py — FastAPI application entry point
==========================================
Registers all routers and configures middleware.
"""

import os
import sys
from pathlib import Path

# Ensure backend directory is on sys.path for direct imports (routes, auth, database, limiter)
# when running from the repository root (e.g., Render startCommand: uvicorn backend.main:app)
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from routes import auth, users, announcements, events, mock_trials, assignments
from routes import case_files, chat, points, certificates, settings, admin

from limiter import limiter

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

app = FastAPI(title="Law in Order API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS for both local development (including file://) and production
origins = [
    "null",
    FRONTEND_URL,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in set(origins) if o],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups.
app.include_router(auth.router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(users.router,         prefix="/api/users",         tags=["Users"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["Announcements"])
app.include_router(events.router,        prefix="/api/events",        tags=["Events"])
app.include_router(mock_trials.router,   prefix="/api/mock-trials",   tags=["Mock Trials"])
app.include_router(assignments.router,   prefix="/api/assignments",   tags=["Assignments"])
app.include_router(case_files.router,    prefix="/api/files",         tags=["Case Files"])
app.include_router(chat.router,          prefix="/api/chat",          tags=["Chat"])
app.include_router(points.router,        prefix="/api/points",        tags=["Points"])
app.include_router(certificates.router,  prefix="/api/certificates",  tags=["Certificates"])
app.include_router(settings.router,      prefix="/api/settings",      tags=["Settings"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["Admin"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Law in Order API"}


# Serve static frontend files directly through FastAPI
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
