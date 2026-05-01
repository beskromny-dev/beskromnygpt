"""Load channel posts from LiveDune export into ChromaDB.

Usage:
    python -m scripts.load_channel_archive

Reads data/exports/channel_posts.json and indexes into ChromaDB
with metadata (register, date, topic_tags, er_score, type).
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from core.config import DATA_DIR, CHROMA_DIR
from core.rag.store import get_collection


EXPORTS_DIR = DATA_DIR / "exports"


def compute_er(post: dict) -> float:
    """Compute engagement rate for a post."""
    r = post.get("reactions") or {}
    imp = post.get("impressions") or {}
    views = imp.get("total") or 1
    engagement = (r.get("likes") or 0) + (r.get("comments") or 0) + (r.get("forwards") or 0)
    return round(engagement / views * 100, 2)


def time_weight(date_str: str) -> float:
    """Return 1.5 for posts < 12 months old, 1.0 otherwise."""
    try:
        dt = datetime.fromisoformat(date_str)
        if datetime.now() - dt < timedelta(days=365):
            return 1.5
        return 1.0
    except (ValueError, TypeError):
        return 1.0


def main():
    posts_path = EXPORTS_DIR / "channel_posts.json"
    if not posts_path.exists():
        print("ERROR: No posts found. Run: python -m scripts.fetch_livedune_posts")
        return

    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(posts)} posts from LiveDune export")

    # Filter posts with substantial text
    text_posts = [p for p in posts if len(p.get("text") or "") > 50]
    print(f"Posts with text > 50 chars: {len(text_posts)}")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    collection = get_collection()

    # Check what's already loaded
    existing = collection.count()
    print(f"Existing documents in ChromaDB: {existing}")

    # Prepare batches (ChromaDB likes batches of ~100)
    batch_size = 100
    ids = []
    documents = []
    metadatas = []

    for post in text_posts:
        text = post.get("text") or ""
        post_id = post.get("post_id") or post.get("id")
        date = post.get("created") or ""
        er = compute_er(post)
        weight = time_weight(date)
        post_type = post.get("type") or "text"
        url = post.get("url") or ""

        doc_id = f"channel_{post_id}"
        ids.append(doc_id)
        documents.append(text)
        metadatas.append({
            "register": "channel",
            "date": date,
            "er_score": er,
            "time_weight": weight,
            "type": post_type,
            "post_id": str(post_id),
            "url": url,
            "source": "livedune",
        })

    # Upsert in batches
    total = len(ids)
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        collection.upsert(
            ids=ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )
        print(f"  Upserted {end}/{total}...")

    final_count = collection.count()
    print(f"\nDone. Total documents in ChromaDB: {final_count}")
    print(f"Collection: {collection.name}")


if __name__ == "__main__":
    main()
