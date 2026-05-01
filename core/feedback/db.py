"""SQLite feedback storage (Block D)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.config import DATA_DIR

DB_PATH = DATA_DIR / "feedback.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            command TEXT NOT NULL,
            prompt TEXT,
            generated TEXT NOT NULL,
            edited TEXT,
            rating TEXT NOT NULL CHECK(rating IN ('used', 'edited', 'rejected'))
        )
    """)
    conn.commit()
    return conn


def save_feedback(
    command: str,
    prompt: str | None,
    generated: str,
    rating: str,
    edited: str | None = None,
) -> int:
    """Save a feedback entry. Returns the row id."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO feedback (created_at, command, prompt, generated, edited, rating) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), command, prompt, generated, edited, rating),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_feedback_stats() -> dict:
    """Get aggregated feedback statistics."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT command, rating, COUNT(*) as cnt FROM feedback GROUP BY command, rating"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    conn.close()

    by_command = {}
    for command, rating, cnt in rows:
        if command not in by_command:
            by_command[command] = {"used": 0, "edited": 0, "rejected": 0, "total": 0}
        by_command[command][rating] = cnt
        by_command[command]["total"] += cnt

    return {"total": total, "by_command": by_command}
