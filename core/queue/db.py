"""Content queue — SQLite storage for editor workflow."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from core.config import DATA_DIR

DB_PATH = DATA_DIR / "queue.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            command TEXT NOT NULL,
            topic TEXT,
            generated TEXT NOT NULL,
            edited TEXT,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft', 'edited', 'approved', 'rejected', 'published')),
            reviewer_note TEXT
        )
    """)
    conn.commit()
    return conn


def add_to_queue(
    author_id: int,
    command: str,
    topic: str | None,
    generated: str,
) -> int:
    """Add a new draft to the queue. Returns the queue item id."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO queue (created_at, updated_at, author_id, command, topic, generated, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 'draft')",
        (now, now, author_id, command, topic, generated),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def update_status(
    item_id: int,
    status: str,
    reviewer_note: str | None = None,
) -> bool:
    """Update queue item status. Returns True if item was found."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE queue SET status = ?, reviewer_note = ?, updated_at = ? WHERE id = ?",
        (status, reviewer_note, now, item_id),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def save_edit(item_id: int, edited_text: str) -> bool:
    """Save edited version of a draft. Returns True if item was found."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE queue SET edited = ?, status = 'edited', updated_at = ? WHERE id = ?",
        (edited_text, now, item_id),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def get_queue(status: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Get queue items, optionally filtered by status."""
    conn = _get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM queue WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM queue WHERE status NOT IN ('published', 'rejected') "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item(item_id: int) -> Optional[dict]:
    """Get a single queue item by id."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM queue WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
