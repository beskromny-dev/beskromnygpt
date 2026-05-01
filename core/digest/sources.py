"""Digest source configuration — Tier 1 RSS feeds and Tier 2 search queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RSSSource:
    name: str
    url: str
    feed_url: str
    category: str  # business | tech | marketing | culture | psychology | lifestyle
    lang: str = "en"  # "en" or "ru"


# ── Tier 1: Daily RSS scrape ──────────────────────────────────────

TIER1_SOURCES: list[RSSSource] = [

    # ━━━ INTERNATIONAL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Business / Tech
    RSSSource(
        name="MIT Technology Review",
        url="https://www.technologyreview.com",
        feed_url="https://www.technologyreview.com/feed",
        category="tech",
    ),
    RSSSource(
        name="Fast Company",
        url="https://www.fastcompany.com",
        feed_url="https://www.fastcompany.com/latest/rss",
        category="business",
    ),
    RSSSource(
        name="Futurism",
        url="https://futurism.com",
        feed_url="https://futurism.com/feed",
        category="tech",
    ),
    RSSSource(
        name="Semafor",
        url="https://www.semafor.com",
        feed_url="https://www.semafor.com/rss.xml",
        category="business",
    ),
    RSSSource(
        name="Axios",
        url="https://www.axios.com",
        feed_url="https://api.axios.com/feed/",
        category="business",
    ),

    # Marketing / Advertising
    RSSSource(
        name="Adweek",
        url="https://www.adweek.com",
        feed_url="https://www.adweek.com/feed/",
        category="marketing",
    ),
    RSSSource(
        name="Digiday",
        url="https://digiday.com",
        feed_url="https://digiday.com/feed/",
        category="marketing",
    ),
    RSSSource(
        name="Famous Campaigns",
        url="https://www.famouscampaigns.com",
        feed_url="https://www.famouscampaigns.com/feed/",
        category="marketing",
    ),

    # Culture / Psychology / Lifestyle
    RSSSource(
        name="Aeon",
        url="https://aeon.co",
        feed_url="https://aeon.co/feed.rss",
        category="culture",
    ),
    RSSSource(
        name="Dezeen",
        url="https://www.dezeen.com",
        feed_url="https://www.dezeen.com/feed/",
        category="culture",
    ),
    RSSSource(
        name="The Conversation",
        url="https://theconversation.com",
        feed_url="https://theconversation.com/us/articles.atom",
        category="psychology",
    ),
    RSSSource(
        name="Eater",
        url="https://www.eater.com",
        feed_url="https://www.eater.com/rss/index.xml",
        category="lifestyle",
    ),

    # ━━━ THOUGHT LEADERS / NEWSLETTERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━

    RSSSource(
        name="Seth Godin",
        url="https://seths.blog",
        feed_url="https://seths.blog/feed/atom/",
        category="business",
    ),
    RSSSource(
        name="Tim Ferriss",
        url="https://tim.blog",
        feed_url="https://tim.blog/feed/",
        category="lifestyle",
    ),
    RSSSource(
        name="James Clear",
        url="https://jamesclear.com",
        feed_url="https://jamesclear.com/feed",
        category="psychology",
    ),
    RSSSource(
        name="Farnam Street",
        url="https://fs.blog",
        feed_url="https://fs.blog/feed/",
        category="psychology",
    ),
    RSSSource(
        name="Not Boring (Packy McCormick)",
        url="https://www.notboring.co",
        feed_url="https://www.notboring.co/feed",
        category="business",
    ),
    RSSSource(
        name="Lenny's Newsletter",
        url="https://www.lennysnewsletter.com",
        feed_url="https://www.lennysnewsletter.com/feed",
        category="business",
    ),
    RSSSource(
        name="Zvi Mowshowitz (AI)",
        url="https://thezvi.substack.com",
        feed_url="https://thezvi.substack.com/feed",
        category="tech",
    ),
    RSSSource(
        name="Every.to",
        url="https://every.to",
        feed_url="https://every.to/everything/feed",
        category="business",
    ),
    RSSSource(
        name="Stratechery",
        url="https://stratechery.com",
        feed_url="https://stratechery.com/feed/",
        category="tech",
    ),
    RSSSource(
        name="Andrew Chen",
        url="https://andrewchen.com",
        feed_url="https://andrewchen.com/feed/",
        category="business",
    ),
    RSSSource(
        name="The Diff (Byrne Hobart)",
        url="https://thediff.co",
        feed_url="https://thediff.co/feed",
        category="business",
    ),
    RSSSource(
        name="Wait But Why",
        url="https://waitbutwhy.com",
        feed_url="https://waitbutwhy.com/feed",
        category="culture",
    ),
    RSSSource(
        name="Gary Vaynerchuk (Substack)",
        url="https://garyvaynerchuk.substack.com",
        feed_url="https://garyvaynerchuk.substack.com/feed",
        category="business",
    ),
    RSSSource(
        name="Gary Vaynerchuk (Medium)",
        url="https://medium.com/@garyvee",
        feed_url="https://medium.com/feed/@garyvee",
        category="business",
    ),

    # ━━━ РОССИЯ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Федеральные бизнес-медиа
    RSSSource(
        name="РБК",
        url="https://www.rbc.ru",
        feed_url="https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        category="business",
        lang="ru",
    ),
    RSSSource(
        name="Коммерсантъ",
        url="https://www.kommersant.ru",
        feed_url="https://www.kommersant.ru/RSS/news.xml",
        category="business",
        lang="ru",
    ),
    RSSSource(
        name="Forbes Russia",
        url="https://www.forbes.ru",
        feed_url="https://www.forbes.ru/newrss.xml",
        category="business",
        lang="ru",
    ),
    RSSSource(
        name="Ведомости",
        url="https://www.vedomosti.ru",
        feed_url="https://www.vedomosti.ru/rss/news",
        category="business",
        lang="ru",
    ),
    RSSSource(
        name="The Bell",
        url="https://thebell.io",
        feed_url="https://thebell.io/feed",
        category="business",
        lang="ru",
    ),

    # Маркетинг / Реклама
    RSSSource(
        name="Состав.ру",
        url="https://www.sostav.ru",
        feed_url="https://www.sostav.ru/rss",
        category="marketing",
        lang="ru",
    ),
    RSSSource(
        name="AdIndex",
        url="https://adindex.ru",
        feed_url="https://adindex.ru/news/news.rss",
        category="marketing",
        lang="ru",
    ),
    RSSSource(
        name="Cossa",
        url="https://www.cossa.ru",
        feed_url="https://www.cossa.ru/rss/",
        category="marketing",
        lang="ru",
    ),
    RSSSource(
        name="Adpass",
        url="https://adpass.ru",
        feed_url="https://adpass.ru/feed/",
        category="marketing",
        lang="ru",
    ),

    # Tech / Стартапы
    RSSSource(
        name="vc.ru",
        url="https://vc.ru",
        feed_url="https://vc.ru/rss",
        category="tech",
        lang="ru",
    ),
    RSSSource(
        name="RB.ru",
        url="https://rb.ru",
        feed_url="https://rb.ru/feeds/all/",
        category="tech",
        lang="ru",
    ),
    RSSSource(
        name="Хабр (AI)",
        url="https://habr.com",
        feed_url="https://habr.com/ru/rss/hub/artificial_intelligence/",
        category="tech",
        lang="ru",
    ),

    # Культура / Психология / Лайфстайл
    RSSSource(
        name="Афиша Daily",
        url="https://daily.afisha.ru",
        feed_url="https://daily.afisha.ru/rss/",
        category="culture",
        lang="ru",
    ),
    RSSSource(
        name="Psychologies Russia",
        url="https://www.psychologies.ru",
        feed_url="https://www.psychologies.ru/rss/",
        category="psychology",
        lang="ru",
    ),
    RSSSource(
        name="Inc. Russia",
        url="https://incrussia.ru",
        feed_url="https://incrussia.ru/feed/",
        category="business",
        lang="ru",
    ),
]


# ── Tier 2: Web search queries ────────────────────────────────────

TIER2_SEARCH_QUERIES: list[dict] = [
    # International (paywalled: Economist, Bloomberg, Forbes, Fortune, HBR, WSJ)
    {
        "query": "AI business strategy impact 2026",
        "category": "tech",
    },
    {
        "query": "marketing trends brands advertising campaigns",
        "category": "marketing",
    },
    {
        "query": "consumer behavior psychology research trends",
        "category": "psychology",
    },
    {
        "query": "startup funding corporate strategy news",
        "category": "business",
    },
    {
        "query": "cultural shifts lifestyle trends society 2026",
        "category": "culture",
    },
    {
        "query": "technology regulation AI policy impact",
        "category": "tech",
    },
    {
        "query": "luxury design architecture trends",
        "category": "lifestyle",
    },
    # Sources without working RSS
    {
        "query": "site:marketingdive.com marketing news",
        "category": "marketing",
    },
    {
        "query": "site:psychologytoday.com behavioral psychology decisions",
        "category": "psychology",
    },
    {
        "query": "knife.media новые статьи",
        "category": "culture",
    },
    {
        "query": "маркетинг тренды реклама Россия 2026",
        "category": "marketing",
    },
]


# ── Tier 2 source labels (for prompt context) ────────────────────

TIER2_PAYWALLED_SOURCES: list[str] = [
    # International
    "The Economist",
    "Bloomberg",
    "Fortune",
    "HBR",
    "WSJ",
    "The New Yorker",
    "Monocle",
    "The Atlantic",
    "Nautilus",
    "Scientific American",
    "Robb Report",
    "Marketing Dive",
    "Psychology Today",
    # Russian (no RSS)
    "Нож (knife.media)",
    "Esquire Russia",
]
