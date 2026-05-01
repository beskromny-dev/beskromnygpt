"""LiveDune API client for Telegram channel analytics."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.livedune.com"
ACCOUNT_ID = 2481788  # @dbeskromny
TIMEOUT = 15.0


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    p = {"access_token": settings.livedune_api_key}
    if params:
        p.update(params)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=p)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", data) if isinstance(data, dict) and "response" in data else data


async def get_channel_stats() -> Dict[str, Any]:
    data = await _get("/accounts")
    accounts = data if isinstance(data, list) else []
    account = next((a for a in accounts if a.get("id") == ACCOUNT_ID), None)
    if not account:
        return {"error": "Канал не найден в аккаунте LiveDune"}
    stat = account.get("stat", {})
    return {
        "name": account.get("name", ""),
        "short_name": account.get("short_name", ""),
        "subscribers": stat.get("followers", 0),
        "posts_count": stat.get("posts", 0),
        "url": account.get("url", ""),
        "error": None,
    }


async def get_top_posts(limit: int = 5) -> Dict[str, Any]:
    data = await _get(f"/accounts/{ACCOUNT_ID}/posts", {"limit": limit})
    raw = data if isinstance(data, list) else []
    posts = []
    for p in raw:
        reactions = p.get("reactions", {}) or {}
        likes = reactions.get("likes", 0) or 0
        comments = reactions.get("comments", 0) or 0
        forwards = reactions.get("forwards", 0) or 0
        views = (p.get("impressions") or {}).get("total", 0) or 0
        total_reactions = likes + comments + forwards
        er = round(total_reactions / views * 100, 2) if views > 0 else 0
        posts.append({
            "text": (p.get("text", "") or "")[:150],
            "date": (p.get("created", "") or "")[:10],
            "url": p.get("url", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "forwards": forwards,
            "er": er,
        })
    posts.sort(key=lambda x: x["er"], reverse=True)
    return {"posts": posts, "error": None}


async def get_growth_data() -> Dict[str, Any]:
    data = await _get(f"/accounts/{ACCOUNT_ID}/posts", {"limit": 30})
    raw = data if isinstance(data, list) else []
    total_views = total_reactions = 0
    for p in raw:
        reactions = p.get("reactions", {}) or {}
        imp = p.get("impressions", {}) or {}
        total_views += imp.get("total", 0) or 0
        total_reactions += (
            (reactions.get("likes", 0) or 0)
            + (reactions.get("comments", 0) or 0)
            + (reactions.get("forwards", 0) or 0)
        )
    avg_er = round(total_reactions / total_views * 100, 2) if total_views > 0 else 0
    return {
        "posts_30d": len(raw),
        "total_views": total_views,
        "total_reactions": total_reactions,
        "avg_er": avg_er,
        "error": None,
    }
