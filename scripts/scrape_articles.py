"""Scrape articles from profile links and load into ChromaDB.

Usage:
    python -m scripts.scrape_articles
"""

from __future__ import annotations

import json
import time
import re
from pathlib import Path

import httpx

from core.config import DATA_DIR
from core.rag.store import get_collection

EXPORTS_DIR = DATA_DIR / "exports"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def extract_text(html: str) -> str:
    """Extract readable text from HTML, stripping tags."""
    # Remove script/style
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
    # Remove tags
    text = re.sub(r"<[^>]+>", "\n", html)
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove very short lines (nav, buttons)
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 30]
    return "\n".join(lines)


def find_article_text(html: str) -> str:
    """Try to extract main article content from HTML."""
    # Try common article containers
    for pattern in [
        r'<article[^>]*>(.*?)</article>',
        r'class="article[_-]?(?:body|content|text)[^"]*"[^>]*>(.*?)</div>',
        r'class="post[_-]?(?:body|content|text)[^"]*"[^>]*>(.*?)</div>',
        r'class="content[_-]?(?:body|inner|main)[^"]*"[^>]*>(.*?)</div>',
        r'itemprop="articleBody"[^>]*>(.*?)</div>',
    ]:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            return extract_text(match.group(1))

    # Fallback: extract all text
    return extract_text(html)


def scrape_url(url: str) -> dict:
    """Scrape a single URL and return text + metadata."""
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        if not resp.is_success:
            return {"url": url, "text": "", "error": f"HTTP {resp.status_code}"}

        html = resp.text

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        title = re.sub(r"<[^>]+>", "", title)

        # Extract article text
        text = find_article_text(html)

        return {"url": url, "title": title, "text": text, "error": None}

    except Exception as e:
        return {"url": url, "text": "", "error": str(e)}


def determine_register(url: str) -> str:
    """Determine content register based on URL domain."""
    if any(d in url for d in ["forbes.ru", "rbc.ru", "pro.rbc.ru", "style.rbc.ru"]):
        return "publicistics"
    if any(d in url for d in ["setters.media", "theblueprint.ru", "pravilamag.ru"]):
        return "publicistics"
    if any(d in url for d in ["sostav.ru", "incrussia.ru", "teller.media"]):
        return "publicistics"
    return "publicistics"  # all articles are publicistics register


def main():
    links = json.load(open(EXPORTS_DIR / "profile_links.json", encoding="utf-8"))

    # Filter to article URLs only (skip video, podcasts, tg, background)
    skip_domains = [
        "bq.digital", "t.me/dbeskromny", "gefforum.com", "education.yandex",
        "t.me/medialogia", "t.me/bloggers_mama", "t.me/setters", "academy.calltouch",
        "nat.ru", "hse.ru", "hp.com", "topblog.rsv",
        "youtube.com", "youtu.be", "rutube.ru", "vkvideo.ru", "dzen.ru/video",
        "m24.ru", "tass.ru", "mave.digital", "podcast.ru", "podcasts.apple",
        "career.mave", "t.me/", "online-event.megafon",
    ]

    articles = []
    seen_urls = set()
    for l in links:
        url = l["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        skip = any(d in url for d in skip_domains)
        if skip:
            continue
        articles.append(l)

    print(f"Articles to scrape: {len(articles)}")

    results = []
    for i, art in enumerate(articles, 1):
        url = art["url"]
        print(f"  [{i}/{len(articles)}] {url[:70]}...")
        data = scrape_url(url)
        data["link_text"] = art["text"]

        if data["error"]:
            print(f"    ERROR: {data['error']}")
        elif len(data["text"]) < 200:
            print(f"    WARN: short text ({len(data['text'])} chars)")
        else:
            print(f"    OK: {len(data['text'])} chars | {data['title'][:50]}")

        results.append(data)
        time.sleep(0.5)

    # Save raw results
    (EXPORTS_DIR / "scraped_articles.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Load into ChromaDB
    collection = get_collection()
    loaded = 0

    for r in results:
        text = r.get("text", "")
        if len(text) < 200:
            continue

        url = r["url"]
        title = r.get("title", "") or r.get("link_text", "")
        register = determine_register(url)

        # Chunk long articles
        chunks = []
        if len(text) > 2000:
            words = text.split()
            chunk = []
            chunk_len = 0
            for w in words:
                chunk.append(w)
                chunk_len += len(w) + 1
                if chunk_len > 1500:
                    chunks.append(" ".join(chunk))
                    chunk = []
                    chunk_len = 0
            if chunk:
                chunks.append(" ".join(chunk))
        else:
            chunks = [text]

        for ci, chunk in enumerate(chunks):
            doc_id = f"article_{hash(url)}_{ci}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "register": register,
                    "type": "article",
                    "source": url,
                    "title": title[:200],
                    "date": "",
                    "er_score": 0,
                    "time_weight": 1.0,
                }],
            )
            loaded += 1

    print(f"\nDone. Loaded {loaded} chunks from {len([r for r in results if len(r.get('text','')) >= 200])} articles into ChromaDB.")
    print(f"Total docs in collection: {collection.count()}")


if __name__ == "__main__":
    main()
