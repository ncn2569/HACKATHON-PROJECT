import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv


# Load environment variables for local/dev deployments.
load_dotenv()


# Build DB configuration from env first, then fallback values.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db.tswkyezfgmtnusltqenc.supabase.co"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Phuctqt123@"),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
}


# Open one PostgreSQL connection using shared configuration.
def get_conn():
    return psycopg2.connect(**DB_CONFIG)


# Run a SELECT query and return rows as list[dict].
def run_query(query: str, params: tuple | None = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
    return [dict(row) for row in rows]


# Run INSERT/UPDATE/DELETE and optionally return rows.
def run_execute(query: str, params: tuple | None = None, fetch: bool = False) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            if fetch:
                rows = cursor.fetchall()
            else:
                rows = []
        conn.commit()
    return [dict(row) for row in rows]


# Simple health check to know whether database is reachable.
def is_db_available() -> bool:
    try:
        run_query("SELECT 1 AS ok")
        return True
    except Exception:
        return False