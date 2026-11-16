"""
setup_db.py — Run this ONCE to create all database tables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "").strip()
if not db_url:
    print("\n[ERROR] DATABASE_URL is empty!")
    print("1. Get a free PostgreSQL database from https://neon.tech")
    print("2. Open 'backend/.env' in a text editor.")
    print("3. Paste your connection string on the line: DATABASE_URL=...")
    print("4. Run this script again.\n")
    sys.exit(1)

from database import get_conn

schema_path = Path(__file__).parent.parent / "database" / "schema.sql"

try:
    print("Connecting to PostgreSQL and executing schema.sql...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            sql = schema_path.read_text(encoding="utf-8")
            cur.execute(sql)
        conn.commit()
    print("\n[OK] All 17 database tables created successfully!")
    print("Next step: Double-click 'start_backend.bat' or run: uvicorn main:app --reload\n")
except Exception as e:
    print(f"\n[ERROR] Database error: {e}\n")
    sys.exit(1)
