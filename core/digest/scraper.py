"""Digest scraper — fetches articles from Tier 1 RSS feeds and Tier 2 web searches."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from core.digest.sources import TIER1_SOURCES, TIER2_SEARCH_QUERIES, RSSSource

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, application/atom+xml, text/xml, */*",
}

# Max age for articles to be considered "fresh"
MAX_AGE_HOURS = 48


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    summary: str = ""
    published: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "summary": self.summary,
            "published": self.published,
        }


# ── RSS Parsing ───────────────────────────────────────────────────

def _strip_tags(html: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


def _extract_items_from_xml(xml_text: str) -> list[dict]:
    """Simple regex-based RSS/Atom parser. No lxml dependency needed."""
    items = []

    # Try RSS <item> blocks first
    rss_items = re.findall(r"<item[^>]*>(.*?)</item>", xml_text, re.DOTALL)
    if rss_items:
        for block in rss_items:
            title = _extract_tag(block, "title")
            link = _extract_tag(block, "link") or _extract_attr(block, "link", "href")
            desc = _extract_tag(block, "description") or _extract_tag(block, "content:encoded")
            pub = _extract_tag(block, "pubDate") or _extract_tag(block, "dc:date")
            if title and link:
                items.append({
                    "title": _strip_tags(title),
                    "link": _strip_tags(link).strip(),
                    "summary": _strip_tags(desc)[:500] if desc else "",
                    "published": pub,
                })
        return items

    # Try Atom <entry> blocks
    atom_items = re.findall(r"<entry[^>]*>(.*?)</entry>", xml_text, re.DOTALL)
    for block in atom_items:
        title = _extract_tag(block, "title")
        link = _extract_attr(block, "link", "href")
        desc = _extract_tag(block, "summary") or _extract_tag(block, "content")
        pub = _extract_tag(block, "published") or _extract_tag(block, "updated")
        if title and link:
            items.append({
                "title": _strip_tags(title),
                "link": _strip_tags(link).strip(),
                "summary": _strip_tags(desc)[:500] if desc else "",
                "published": pub,
            })

    return items


def _extract_tag(text: str, tag: str) -> Optional[str]:
    """Extract content between XML tags, handling CDATA."""
    pattern = rf"<{tag}[^>]*>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</{tag}>"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_attr(text: str, tag: str, attr: str) -> Optional[str]:
    """Extract attribute value from a self-closing or open tag."""
    pattern = rf'<{tag}[^>]*{attr}=["\']([^"\']+)["\']'
    m = re.search(pattern, text)
    return m.group(1) if m else None


def fetch_rss(source: RSSSource, max_items: int = 10) -> list[Article]:
    """Fetch and parse a single RSS feed. Returns articles."""
    try:
        resp = httpx.get(
            source.feed_url,
            headers=HEADERS,
            timeout=25,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", source.name, e)
        return []

    items = _extract_items_from_xml(resp.text)

    articles = []
    for item in items[:max_items]:
        articles.append(Article(
            title=item["title"],
            url=item["link"],
            source=source.name,
            category=source.category,
            summary=item["summary"][:400],
            published=item.get("published"),
        ))

    logger.info("Fetched %d articles from %s", len(articles), source.name)
    return articles


def fetch_all_rss(max_per_source: int = 8) -> list[Article]:
    """Fetch all Tier 1 RSS feeds. Returns combined article list."""
    all_articles = []
    for source in TIER1_SOURCES:
        articles = fetch_rss(source, max_items=max_per_source)
        all_articles.extend(articles)
    logger.info("Total Tier 1 articles: %d", len(all_articles))
    return all_articles


# ── Web Search (Tier 2) ──────────────────────────────────────────

def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web. Priority: Google CSE > Brave > DuckDuckGo fallback.

    Returns list of dicts with: title, url, snippet.
    """
    from core.config import settings

    # Google Custom Search API (free 100/day)
    if settings.google_cse_api_key and settings.google_cse_cx:
        try:
            resp = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": settings.google_cse_api_key,
                    "cx": settings.google_cse_cx,
                    "q": query,
                    "num": min(max_results, 10),
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", "")[:300],
                }
                for r in data.get("items", [])
            ]
            logger.info("Google CSE '%s': %d results", query, len(results))
            return results
        except Exception as e:
            logger.warning("Google CSE failed for '%s': %s", query, e)

    # Brave Search API (backup)
    if settings.brave_search_api_key:
        try:
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": settings.brave_search_api_key},
                params={"q": query, "count": max_results},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", "")[:300],
                }
                for r in data.get("web", {}).get("results", [])
            ]
            logger.info("Brave search '%s': %d results", query, len(results))
            return results
        except Exception as e:
            logger.warning("Brave search failed for '%s': %s", query, e)
            return []

    # Fallback: DuckDuckGo HTML
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Web search failed for '%s': %s", query, e)
        return []

    results = []
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</(?:td|div|span)',
        resp.text,
        re.DOTALL,
    )

    for url, title, snippet in blocks[:max_results]:
        actual_url = re.search(r"uddg=([^&]+)", url)
        if actual_url:
            from urllib.parse import unquote
            url = unquote(actual_url.group(1))

        results.append({
            "title": _strip_tags(title),
            "url": url,
            "snippet": _strip_tags(snippet)[:300],
        })

    logger.info("Web search '%s': %d results", query, len(results))
    return results


def fetch_tier2_articles() -> list[Article]:
    """Run all Tier 2 web searches. Returns articles."""
    all_articles = []
    for q in TIER2_SEARCH_QUERIES:
        results = search_web(q["query"], max_results=4)
        for r in results:
            all_articles.append(Article(
                title=r["title"],
                url=r["url"],
                source="web search",
                category=q["category"],
                summary=r["snippet"],
            ))
    logger.info("Total Tier 2 articles: %d", len(all_articles))
    return all_articles


# ── Combined ──────────────────────────────────────────────────────

def fetch_all_articles() -> list[Article]:
    """Fetch all articles from Tier 1 + Tier 2."""
    tier1 = fetch_all_rss()
    tier2 = fetch_tier2_articles()
    combined = tier1 + tier2

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for a in combined:
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            unique.append(a)

    logger.info("Combined unique articles: %d (from %d total)", len(unique), len(combined))
    return unique
