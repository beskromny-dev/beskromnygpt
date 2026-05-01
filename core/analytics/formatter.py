"""Format analytics data into Telegram-friendly text reports."""

from __future__ import annotations

from typing import Any, Dict, List


def _truncate(text: str, length: int = 100) -> str:
    text = text.replace("\n", " ").strip()
    return text[:length].rstrip() + "..." if len(text) > length else text


def format_channel_report(
    stats: Dict[str, Any],
    top_posts: Dict[str, Any],
    growth: Dict[str, Any],
) -> str:
    lines: List[str] = ["АНАЛИТИКА @dbeskromny\n"]

    if not stats.get("error"):
        subs = stats.get("subscribers", 0)
        posts = stats.get("posts_count", 0)
        lines.append(f"Подписчики: {subs:,}".replace(",", " "))
        lines.append(f"Всего постов: {posts}")
    else:
        lines.append(f"Статистика: {stats['error']}")

    lines.append("")

    if not growth.get("error"):
        avg_er = growth.get("avg_er", 0)
        total_views = growth.get("total_views", 0)
        posts_n = growth.get("posts_30d", 0)
        total_reactions = growth.get("total_reactions", 0)
        lines.append(f"Последние {posts_n} постов:")
        lines.append(f"  Средний ER: {avg_er}%")
        lines.append(f"  Просмотры: {total_views:,}".replace(",", " "))
        lines.append(f"  Реакции: {total_reactions:,}".replace(",", " "))
    else:
        lines.append(f"Активность: {growth['error']}")

    lines.append("")

    posts_list = top_posts.get("posts", []) if not top_posts.get("error") else []
    if posts_list:
        top_n = min(3, len(posts_list))
        lines.append(f"Топ-{top_n} постов по ER:\n")
        for i, p in enumerate(posts_list[:top_n], 1):
            lines.append(
                f"{i}. ER {p['er']}% — "
                f"{p['likes']} лайков, {p['forwards']} репостов, {p['views']:,} просмотров".replace(",", " ")
            )
            lines.append(f"   {_truncate(p['text'])}")
            if p.get("date"):
                lines.append(f"   {p['date']}")
            if p.get("url"):
                lines.append(f"   {p['url']}")
            lines.append("")

    return "\n".join(lines)
