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
    """Fetch all Tier 1 RSS feeds. Returns combined article list.

    Defensive wrapper: a crash in any single source never aborts the digest.
    """
    all_articles = []
    for source in TIER1_SOURCES:
        try:
            articles = fetch_rss(source, max_items=max_per_source)
            all_articles.extend(articles)
        except Exception as e:
            logger.error("Source %s crashed unexpectedly: %s — skipped", source.name, e)
    logger.info("Total Tier 1 articles: %d (from %d sources)", len(all_articles), len(TIER1_SOURCES))
    return all_articles


# ── Hacker News (front-page filtered by quality) ─────────────────

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_hn_top(min_points: int = 200, min_comments: int = 50, max_items: int = 20) -> list[Article]:
    """Fetch Hacker News front-page stories above a quality threshold.

    Filters by points and comment count to surface stories that actually got
    serious discussion. Best detector of weird-tech-stories-everyone-is-talking-about.

    Defensive: any failure returns [] without aborting the digest.
    """
    try:
        resp = httpx.get(
            HN_ALGOLIA_URL,
            params={
                "tags": "story",
                "numericFilters": f"points>={min_points},num_comments>={min_comments}",
                "hitsPerPage": max_items,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("Hacker News fetch failed: %s — skipped", e)
        return []

    articles = []
    for hit in data.get("hits", []):
        title = hit.get("title")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if not title or not url:
            continue
        points = hit.get("points", 0)
        comments = hit.get("num_comments", 0)
        hn_link = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        summary = f"({points} points, {comments} comments) HN discussion: {hn_link}"
        articles.append(Article(
            title=title,
            url=url,
            source="Hacker News",
            category="tech",
            summary=summary,
            published=hit.get("created_at"),
        ))

    logger.info("Fetched %d Hacker News stories (≥%d pts, ≥%d comments)",
                len(articles), min_points, min_comments)
    return articles


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
    """Run all Tier 2 web searches. Returns articles.

    Defensive wrapper: a crash in any single query never aborts the digest.
    """
    all_articles = []
    for q in TIER2_SEARCH_QUERIES:
        try:
            results = search_web(q["query"], max_results=4)
            for r in results:
                all_articles.append(Article(
                    title=r["title"],
                    url=r["url"],
                    source="web search",
                    category=q["category"],
                    summary=r["snippet"],
                ))
        except Exception as e:
            logger.error("Tier 2 query '%s' crashed unexpectedly: %s — skipped", q.get("query", "?"), e)
    logger.info("Total Tier 2 articles: %d", len(all_articles))
    return all_articles


# ── Combined ──────────────────────────────────────────────────────

def fetch_all_articles() -> list[Article]:
    """Fetch all articles from Tier 1 (RSS) + Tier 2 (web search) + Tier 3 (HN).

    Each tier wraps its own errors — a failure in one tier never aborts the others.
    """
    try:
        tier1 = fetch_all_rss()
    except Exception as e:
        logger.error("Tier 1 (RSS) layer crashed: %s", e)
        tier1 = []

    try:
        tier2 = fetch_tier2_articles()
    except Exception as e:
        logger.error("Tier 2 (web search) layer crashed: %s", e)
        tier2 = []

    try:
        tier3 = fetch_hn_top()
    except Exception as e:
        logger.error("Tier 3 (Hacker News) layer crashed: %s", e)
        tier3 = []

    combined = tier1 + tier2 + tier3

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for a in combined:
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            unique.append(a)

    logger.info(
        "Combined unique articles: %d (Tier1=%d, Tier2=%d, Tier3=%d, total=%d)",
        len(unique), len(tier1), len(tier2), len(tier3), len(combined),
    )
    return unique
