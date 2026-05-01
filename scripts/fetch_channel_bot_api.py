"""Fallback: fetch channel posts via Telegram Bot API.

Usage:
    python -m scripts.fetch_channel_bot_api

Use this if LiveDune API is unavailable. Bot must be admin in the channel.
Exports to data/exports/channel_posts_tg.json
"""

import json
import time

import httpx

from core.config import DATA_DIR, settings

EXPORTS_DIR = DATA_DIR / "exports"
TG_API = "https://api.telegram.org/bot{token}"


def get_updates(token: str, channel_id: str) -> list[dict]:
    """Fetch channel posts via getUpdates (limited to recent)."""
    # For full history, we use getChat + forward approach
    # Bot API doesn't give full history — this is a bootstrap helper
    base = TG_API.format(token=token)

    # Verify bot has access
    resp = httpx.get(f"{base}/getChat", params={"chat_id": channel_id}, timeout=15)
    resp.raise_for_status()
    chat = resp.json()
    print(f"Channel: {chat['result'].get('title', channel_id)}")

    # Get message count estimate
    resp = httpx.get(f"{base}/getChatMemberCount", params={"chat_id": channel_id}, timeout=15)
    if resp.is_success:
        print(f"Subscribers: {resp.json().get('result', '?')}")

    return []


def scrape_public_channel(channel_username: str) -> list[dict]:
    """Scrape posts from t.me/s/ (public web preview). Works without bot."""
    posts = []
    url = f"https://t.me/s/{channel_username.lstrip('@')}"
    before = None

    print(f"Scraping {url}...")

    while True:
        params = {}
        if before:
            params["before"] = before

        resp = httpx.get(url, params=params, timeout=30)
        if not resp.is_success:
            break

        html = resp.text

        # Extract post blocks — simple parsing
        import re
        # Find message IDs
        msg_ids = re.findall(r'data-post="[^/]+/(\d+)"', html)
        # Find message texts
        msg_texts = re.findall(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            html,
            re.DOTALL,
        )
        # Find dates
        msg_dates = re.findall(r'<time[^>]*datetime="([^"]+)"', html)
        # Find view counts
        msg_views = re.findall(
            r'<span class="tgme_widget_message_views">([^<]+)</span>', html
        )

        if not msg_ids:
            break

        for i, msg_id in enumerate(msg_ids):
            text = ""
            if i < len(msg_texts):
                # Strip HTML tags
                text = re.sub(r"<[^>]+>", "", msg_texts[i]).strip()

            post = {
                "id": int(msg_id),
                "text": text,
                "date": msg_dates[i] if i < len(msg_dates) else None,
                "views": msg_views[i] if i < len(msg_views) else None,
            }
            posts.append(post)

        oldest_id = min(int(x) for x in msg_ids)
        if before and before == oldest_id:
            break
        before = oldest_id

        print(f"  Scraped {len(posts)} posts (oldest id: {oldest_id})...")
        time.sleep(1)

    # Deduplicate by id
    seen = set()
    unique = []
    for p in posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    return sorted(unique, key=lambda x: x["id"], reverse=True)


def main():
    channel = settings.telegram_channel_id or "@beskromny"
    print(f"Fetching posts from {channel}...")

    posts = scrape_public_channel(channel)
    print(f"\nTotal unique posts: {len(posts)}")

    if posts:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = EXPORTS_DIR / "channel_posts_tg.json"
        out_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved to {out_path}")

        # Show sample
        print("\nSample (3 most recent):")
        for p in posts[:3]:
            text_preview = (p["text"][:80] + "...") if len(p["text"]) > 80 else p["text"]
            print(f"  [{p['date']}] {p['views']} views — {text_preview}")


if __name__ == "__main__":
    main()
