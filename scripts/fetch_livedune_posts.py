"""Fetch all posts from LiveDune API for the Telegram channel.

Usage:
    python -m scripts.fetch_livedune_posts

Exports posts with engagement metrics to data/exports/channel_posts.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from core.config import DATA_DIR, settings

BASE_URL = "https://api.livedune.com"
EXPORTS_DIR = DATA_DIR / "exports"


def get_accounts(token: str) -> list[dict]:
    """Fetch all accounts from LiveDune."""
    resp = httpx.get(
        f"{BASE_URL}/accounts",
        params={"access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_posts(token: str, account_id: str | int) -> list[dict]:
    """Fetch all posts for an account with pagination."""
    all_posts = []
    after = None

    while True:
        params = {"access_token": token}
        if after:
            params["after"] = after

        resp = httpx.get(
            f"{BASE_URL}/accounts/{account_id}/posts",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list):
            posts = data
        elif isinstance(data, dict):
            posts = data.get("response", data.get("data", data.get("posts", [])))
        else:
            break

        if not posts:
            break

        all_posts.extend(posts)
        print(f"  Fetched {len(all_posts)} posts...")

        # Pagination: use "after" cursor from response
        if isinstance(data, dict) and "after" in data and data["after"]:
            after = data["after"]
        elif len(posts) >= 100:
            last = posts[-1]
            after = last.get("id") or last.get("post_id")
        else:
            break

        time.sleep(0.5)  # Rate limiting

    return all_posts


def main():
    token = settings.livedune_api_key
    if not token:
        print("ERROR: LIVEDUNE_API_KEY not set in .env")
        print("Get your API key from LiveDune dashboard.")
        return

    print("Fetching accounts from LiveDune...")
    accounts = get_accounts(token)
    print(f"Found {len(accounts)} accounts:")

    if isinstance(accounts, dict):
        accounts_list = accounts.get("response", accounts.get("data", accounts.get("accounts", [])))
    else:
        accounts_list = accounts

    for acc in accounts_list:
        acc_id = acc.get("id", "?")
        acc_name = acc.get("name") or acc.get("title") or acc.get("username", "?")
        acc_type = acc.get("type") or acc.get("social_network", "?")
        print(f"  [{acc_id}] {acc_name} ({acc_type})")

    # Find Telegram channel — try matching by name or let user pick
    telegram_accounts = [
        a for a in accounts_list
        if "telegram" in str(a.get("type", "") or a.get("social_network", "")).lower()
    ]

    if not telegram_accounts:
        print("\nNo Telegram accounts found. Check your LiveDune dashboard.")
        print("Saving full accounts list for reference...")
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (EXPORTS_DIR / "livedune_accounts.json").write_text(
            json.dumps(accounts_list, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return

    account = telegram_accounts[0]
    acc_id = account.get("id")
    print(f"\nUsing Telegram account: {account.get('name', acc_id)}")

    print("Fetching posts...")
    posts = get_posts(token, acc_id)
    print(f"Total posts: {len(posts)}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORTS_DIR / "channel_posts.json"
    out_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
