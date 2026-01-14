import sqlite3
from contextlib import contextmanager
from typing import Dict

DATABASE_FILE = "instances.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database and create instances table if it doesn't exist."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                correlation_id TEXT PRIMARY KEY,
                port INTEGER NOT NULL
            )
        """)
        conn.commit()


def insert_instance(correlation_id: str, port: int):
    """Insert or replace an instance."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO instances (correlation_id, port) VALUES (?, ?)",
            (correlation_id, port),
        )
        conn.commit()


def delete_instance(correlation_id: str) -> bool:
    """Delete an instance by correlation_id. Returns True if deleted, False if not found."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM instances WHERE correlation_id = ?", (correlation_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_all_instances() -> Dict[str, int]:
    """Get all instances as a dictionary."""
    with get_db() as conn:
        cursor = conn.execute("SELECT correlation_id, port FROM instances")
        return {row[0]: row[1] for row in cursor.fetchall()}


def get_instance_port(correlation_id: str) -> int | None:
    """Get the port for a correlation_id, or None if not found."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT port FROM instances WHERE correlation_id = ?", (correlation_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None


def instance_exists(correlation_id: str) -> bool:
    """Check if an instance exists for the given correlation_id."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM instances WHERE correlation_id = ? LIMIT 1",
            (correlation_id,),
        )
        return cursor.fetchone() is not None
