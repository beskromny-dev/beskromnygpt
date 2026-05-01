"""Analyze channel posts and generate Voice Profile draft.

Usage:
    python -m scripts.build_voice_profile

Reads posts from data/exports/channel_posts.json (LiveDune)
or data/exports/channel_posts_tg.json (Telegram scrape),
analyzes linguistic patterns using Claude, and outputs
a structured Voice Profile draft.
"""

import json
from pathlib import Path

import httpx

from core.config import DATA_DIR, settings

EXPORTS_DIR = DATA_DIR / "exports"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_posts() -> list[dict]:
    """Load posts from available export file."""
    # Prefer LiveDune (has ER data)
    livedune_path = EXPORTS_DIR / "channel_posts.json"
    tg_path = EXPORTS_DIR / "channel_posts_tg.json"

    if livedune_path.exists():
        print("Loading from LiveDune export...")
        posts = json.loads(livedune_path.read_text(encoding="utf-8"))
    elif tg_path.exists():
        print("Loading from Telegram scrape...")
        posts = json.loads(tg_path.read_text(encoding="utf-8"))
    else:
        print(f"ERROR: No posts found. Run one of:")
        print(f"  python -m scripts.fetch_livedune_posts")
        print(f"  python -m scripts.fetch_channel_bot_api")
        return []

    print(f"Loaded {len(posts)} posts")
    return posts


def extract_text(post: dict) -> str:
    """Extract text content from a post."""
    return post.get("text") or post.get("content") or post.get("message") or ""


def sort_by_engagement(posts: list[dict]) -> list[dict]:
    """Sort posts by engagement (ER if available, else views)."""

    def engagement_key(post):
        # LiveDune fields
        er = post.get("er") or post.get("engagement_rate") or 0
        if er:
            return float(er)
        # Fallback to views
        views = post.get("views") or post.get("views_count") or "0"
        if isinstance(views, str):
            views = views.replace("K", "000").replace("M", "000000").replace(".", "")
            try:
                return float(views)
            except ValueError:
                return 0
        return float(views)

    return sorted(posts, key=engagement_key, reverse=True)


def analyze_with_claude(top_posts_text: str) -> str:
    """Send top posts to Claude (via OpenRouter) for linguistic analysis."""
    prompt = f"""Ты — лингвист-аналитик. Тебе даны топ-50 постов Telegram-канала по вовлечённости.
Проанализируй их и создай структурированный Voice Profile.

Формат вывода (строго):

## 1. ЛИНГВИСТИЧЕСКИЕ ПАТТЕРНЫ

### Характерные приёмы автора
(что повторяется, что делает тексты узнаваемыми)

### Структура предложений
(средняя длина, ритм, пунктуация)

### Запрещённые конструкции
(GPT-клише, инфостиль, канцелярит — если их нет в текстах, значит автор их избегает)

### Обязательные ограничения
(emoji — да/нет, восклицательные — да/нет, em-dash — как используется)

## 2. СТРУКТУРНЫЕ ПАТТЕРНЫ

### Типовая структура поста
(заголовок → ... → финал — какая формула)

### Типы заголовков
(какие работают лучше всего)

### Типы финалов
(CTA, панчлайн, вопрос, наблюдение)

## 3. ТЕМАТИЧЕСКИЙ ГРАФ

### Ключевые темы
(топ-10 тем по частоте)

### Специфические трактовки
(темы, которые автор видит нестандартно)

### Пересечения тем
(какие темы часто идут вместе)

## 4. ТОНАЛЬНОСТЬ И ПОЗИЦИОНИРОВАНИЕ

### Позиция автора
(эксперт / наблюдатель / провокатор / ...)

### Отношение к аудитории
(на равных / сверху / ...)

### Эмоциональный регистр
(ирония / серьёзность / ...)

## 5. КАЛИБРОВОЧНЫЕ ПРИМЕРЫ

Выбери 5 постов которые максимально точно представляют голос автора.
Для каждого напиши почему именно этот пост — эталон.

---

ПОСТЫ ДЛЯ АНАЛИЗА:

{top_posts_text}"""

    print("Analyzing with Claude via OpenRouter (this may take a minute)...")
    resp = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": "https://beskromny.ai",
            "X-Title": "BeskromnyAI",
        },
        json={
            "model": settings.openrouter_voice_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
        },
        timeout=300,
    )
    data = resp.json()
    if "choices" not in data:
        raise RuntimeError(f"OpenRouter error: {data}")
    return data["choices"][0]["message"]["content"]


def main():
    posts = load_posts()
    if not posts:
        return

    # Filter posts with actual text
    posts_with_text = [p for p in posts if len(extract_text(p)) > 50]
    print(f"Posts with substantial text: {len(posts_with_text)}")

    # Sort by engagement and take top 50
    sorted_posts = sort_by_engagement(posts_with_text)
    top_50 = sorted_posts[:50]

    print(f"\nTop {len(top_50)} posts selected for analysis")

    # Prepare text for Claude
    posts_text = ""
    for i, post in enumerate(top_50, 1):
        text = extract_text(post)
        date = post.get("date") or post.get("created") or "?"
        views = post.get("views") or post.get("views_count") or "?"
        er = post.get("er") or post.get("engagement_rate") or ""

        posts_text += f"\n--- POST {i} (date: {date}, views: {views}"
        if er:
            posts_text += f", ER: {er}"
        posts_text += f") ---\n{text}\n"

    if not settings.openrouter_api_key:
        # No API key — just save the raw posts for manual analysis
        print("\nOPENROUTER_API_KEY not set. Saving raw top-50 posts for manual analysis...")
        out_path = EXPORTS_DIR / "top50_posts.txt"
        out_path.write_text(posts_text, encoding="utf-8")
        print(f"Saved to {out_path}")
        print("You can analyze these with Claude manually in Google Docs.")
        return

    # Analyze with Claude
    profile = analyze_with_claude(posts_text)

    # Save result
    out_path = EXPORTS_DIR / "voice_profile_draft.md"
    out_path.write_text(
        f"# Voice Profile — БескромныйGPT\n\n"
        f"*Автоматический черновик на основе топ-50 постов по вовлечённости*\n"
        f"*Требует верификации автором*\n\n"
        f"{profile}\n",
        encoding="utf-8",
    )
    print(f"\nVoice Profile draft saved to {out_path}")
    print("Next step: review, correct, and transfer to Google Docs.")


if __name__ == "__main__":
    main()
