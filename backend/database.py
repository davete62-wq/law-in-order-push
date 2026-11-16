"""
database.py — PostgreSQL connection helper with connection pooling
=================================================================
Opens a pool of up to 10 connections to Neon at startup and
reuses them for every request instead of opening a new TCP
connection each time (which is the main cause of slowness).
"""

import os
from pathlib import Path
from contextlib import contextmanager
import psycopg2
import psycopg2.pool
import psycopg2.extras
from dotenv import load_dotenv

# Load from backend/.env or parent .env.local
backend_dir = Path(__file__).parent
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env.local")

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Global connection pool — created once when the module loads.
# minconn=2 keeps 2 warm connections ready at all times.
# maxconn=10 allows up to 10 simultaneous requests.
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Please create a .env file based on .env.example with your PostgreSQL connection string."
            )
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=10,
        )
    return _pool


@contextmanager
def get_conn():
    """
    Context manager that checks out a connection from the pool,
    yields it, then returns it to the pool automatically.
    Usage: `with get_conn() as conn: ...`
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
