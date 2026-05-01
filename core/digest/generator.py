"""Digest generator — Gemini Pro (via OpenRouter) writes balanced brief from full article set. Publishes to Telegraph."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone, timedelta

import httpx

from core.config import settings
from core.digest.scraper import fetch_all_articles, Article
from core.digest.sources import TIER2_PAYWALLED_SOURCES

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TELEGRAPH_API = "https://api.telegra.ph"

MSK = timedelta(hours=3)


def _get_today_msk() -> str:
    now = datetime.now(timezone(MSK))
    return now.strftime("%d %B %Y")


def _get_today_iso() -> str:
    now = datetime.now(timezone(MSK))
    return now.strftime("%Y-%m-%d")


def _format_articles_for_prompt(articles: list[Article]) -> str:
    by_category: dict[str, list[Article]] = {}
    for a in articles:
        by_category.setdefault(a.category, []).append(a)

    parts = []
    for cat, items in by_category.items():
        parts.append(f"\n=== {cat.upper()} ===")
        for i, a in enumerate(items, 1):
            parts.append(f"\n{i}. [{a.source}] {a.title}")
            parts.append(f"   URL: {a.url}")
            if a.summary:
                parts.append(f"   {a.summary}")
    return "\n".join(parts)


# ── LLM Backend ───────────────────────────────────────────────────

OPENROUTER_FALLBACK_MODELS = ["google/gemini-2.5-pro", "google/gemini-2.5-flash"]


def _try_openrouter_model(model: str, system: str, user: str, max_retries: int) -> tuple[str, str | None]:
    """Try one OpenRouter model with retries. Returns (text, None) on success or ("", error) on failure."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 12000,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://beskromny.ai",
        "X-Title": "BeskromnyAI",
    }
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
            data = resp.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"], None
            err_msg = data.get("error", {}).get("message", str(data.get("error", data)))
            last_error = err_msg
            if resp.status_code in (429, 500, 502, 503, 504) or "high demand" in err_msg.lower():
                wait = 30 * (attempt + 1)
                logger.warning("OpenRouter %s [%s] %s — retry %d/%d in %ds",
                               model, resp.status_code, err_msg[:80], attempt + 1, max_retries, wait)
                time.sleep(wait)
                continue
            return "", f"{model}: {err_msg}"
        except httpx.HTTPError as e:
            last_error = str(e)
            wait = 30 * (attempt + 1)
            logger.warning("OpenRouter %s HTTP error: %s — retry %d/%d in %ds",
                           model, e, attempt + 1, max_retries, wait)
            time.sleep(wait)
    return "", f"{model} exhausted retries: {last_error}"


def _call_openrouter(system: str, user: str, max_retries: int = 3) -> str:
    """Try primary digest model, then fall back to stable models. Raises only if all fail."""
    primary = settings.openrouter_digest_model
    models_to_try = [primary] + [m for m in OPENROUTER_FALLBACK_MODELS if m != primary]
    errors = []
    for model in models_to_try:
        logger.info("Trying OpenRouter model: %s", model)
        text, err = _try_openrouter_model(model, system, user, max_retries)
        if text:
            if model != primary:
                logger.warning("Used fallback model: %s (primary %s failed)", model, primary)
            return text
        errors.append(err)
    raise RuntimeError(f"All OpenRouter models failed: {' | '.join(errors)}")


# ── Prompt ────────────────────────────────────────────────────────

DIGEST_SYSTEM = (
    "Ты — аналитик-скаут для Telegram-канала «Бескромный» (145K+ подписчиков). "
    "Автор — Дмитрий Бескромный, основатель bQ Group и AI Influence.\n\n"

    "ЭТО НЕ ПОСТ ДЛЯ КАНАЛА. Это рабочий бриф для редактора.\n\n"

    "АУДИТОРИЯ КАНАЛА — максимально широкая:\n"
    "Маркетологи, предприниматели, менеджеры, но также обычные люди, которым интересно "
    "разбираться в мире. Пиши просто и понятно. Никакого жаргона без объяснения.\n\n"

    "ЧТО ЗАХОДИТ НА КАНАЛЕ (в порядке приоритета):\n"
    "1. Абсурд и парадоксы — когда реальность противоречит здравому смыслу "
    "(компания ничего не продаёт и зарабатывает миллиарды; бренд внедряет ИИ и теряет стоимость)\n"
    "2. Конкретные цифры, которые удивляют\n"
    "3. Неочевидные связи между вещами\n"
    "4. Когнитивные искажения, поведенческая психология — как люди на самом деле принимают решения\n"
    "5. Культурные сдвиги и тренды, которые меняют повседневную жизнь\n"
    "6. Провокационные выводы, которые хочется оспорить\n\n"

    "ОБЯЗАТЕЛЬНЫЙ БАЛАНС КАТЕГОРИЙ в блоке «Новости дня»:\n"
    "Включи 10-12 новостей. Это главный блок брифа — не экономь.\n"
    "Минимум:\n"
    "- 3 про бизнес/маркетинг/деньги (абсурдные бизнес-кейсы с цифрами — приоритет)\n"
    "- 2-3 про технологии/ИИ (через призму влияния на жизнь людей, не техно-новость)\n"
    "- 3 про поведенческую психологию, когнитивные искажения, исследования о людях, социальные тренды, поколенческие конфликты\n"
    "- 2-3 про культуру, лайфстайл, дизайн, еду, городскую среду (как сигнал изменений в обществе)\n"
    "Не допускай перекоса: если больше 3 из 12 новостей про ИИ — это плохой бриф. Разнообразие = ценность.\n\n"

    "КЛЮЧЕВЫЕ КОНЦЕПЦИИ АВТОРА:\n"
    "- «ИИ — экзоскелет для мозга»\n"
    "- «Калорийный контент»\n"
    "- «Линди-навыки»\n"
    "- «Двухфакторная авторизация»\n"
    "- «Территория любви»\n\n"

    "ЖЁСТКИЕ ФИЛЬТРЫ (что НЕ включать):\n"
    "- Чистую политику и геополитику без бизнес-призмы\n"
    "- Локальный PR без цифр и парадокса\n"
    "- Криминальную хронику\n"
    "- Узкотехнические новости (релизы SDK, обновления фреймворков)\n"
    "- Новости ради новостей — нужен парадокс, абсурд или инсайт\n\n"

    "СТРУКТУРА БРИФА (7 блоков):\n\n"

    "## Выжимка для Telegram\n"
    "Это сообщение, которое уйдёт в Telegram вместе с PDF. Пиши живо, от первого лица, "
    "как если бы редактор писал Диме утром. Начни с «Доброе утро, Дима! Дайджест на [дата] готов.»\n"
    "Дальше — 3-4 коротких абзаца:\n"
    "1. «Главное из свежего» — 2-3 ключевые новости с цифрами, одним потоком\n"
    "2. «Из истории» — краткое упоминание исторического события или дня рождения\n"
    "3. «Жемчужина» — 1 предложение о главной теме для лонгрида\n"
    "4. Завершение: «Плюс [N] идей для постов — всё в PDF.»\n"
    "Без markdown-заголовков внутри, без ссылок, без списков — только текст абзацами.\n"
    "Объём: 800-1200 символов.\n\n"

    "## Сводка\n"
    "3-4 предложения простым языком: что сегодня интересного и с чего начать.\n\n"

    "## История дня\n"
    "Событие этого дня + неожиданная параллель с современностью.\n"
    "**Почему это контент:** какой пост можно сделать и почему зайдёт.\n"
    "[Источник](url)\n\n"

    "## Дни рождения\n"
    "1-2 персоны, родившихся в этот день.\n"
    "**Почему это контент:** бизнес-урок или инсайт из их жизни.\n"
    "[Источник](url)\n\n"

    "## Новости дня\n"
    "10-12 новостей (соблюдай баланс категорий!). Для каждой:\n"
    "### Заголовок\n"
    "Суть (2-3 предложения). Цифры.\n"
    "**Виральный потенциал:** почему зацепит и какой угол подачи.\n"
    "**Идея поста:** рабочий заголовок + 1 предложение.\n"
    "[Источник](url)\n\n"

    "## Жемчужина\n"
    "Одна глубокая тема для отдельного поста.\n"
    "**Почему это ценно:** что неочевидного.\n"
    "**Формат:** короткий пост / лонгрид / серия.\n"
    "[Источник](url)\n\n"

    "## Рекомендация на день\n"
    "**Сегодня:** что делать.\n"
    "**В бэклог:** что отложить.\n"
    "**Игнорировать:** что пропустить и почему.\n\n"

    "ФОРМАТИРОВАНИЕ:\n"
    "- Все ссылки — [текст](url)\n"
    "- Заголовки: ## и ###\n"
    "- Разделители --- между блоками\n"
    "- Никаких эмодзи, хэштегов, декоративных тире\n"
    "- Простой язык, короткие предложения"
)


# ── Telegraph Publishing ─────────────────────────────────────────

def _markdown_to_telegraph_nodes(text: str) -> list:
    nodes = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            nodes.append({"tag": "hr"})
            continue
        if stripped.startswith("### "):
            nodes.append({"tag": "h4", "children": _parse_inline(stripped[4:])})
            continue
        if stripped.startswith("## "):
            nodes.append({"tag": "h3", "children": _parse_inline(stripped[3:])})
            continue
        if stripped.startswith("> "):
            nodes.append({"tag": "blockquote", "children": [
                {"tag": "p", "children": _parse_inline(stripped[2:])}
            ]})
            continue
        nodes.append({"tag": "p", "children": _parse_inline(stripped)})
    return nodes


def _parse_inline(text: str) -> list:
    parts = []
    pos = 0
    pattern = re.compile(
        r"\*\*(.+?)\*\*"
        r"|\*(.+?)\*"
        r"|\[([^\]]+)\]\(([^)]+)\)"
    )
    for m in pattern.finditer(text):
        if m.start() > pos:
            parts.append(text[pos:m.start()])
        if m.group(1):
            parts.append({"tag": "strong", "children": [m.group(1)]})
        elif m.group(2):
            parts.append({"tag": "em", "children": [m.group(2)]})
        elif m.group(3):
            parts.append({"tag": "a", "attrs": {"href": m.group(4)}, "children": [m.group(3)]})
        pos = m.end()
    if pos < len(text):
        parts.append(text[pos:])
    return parts if parts else [text]


def publish_to_telegraph(title: str, text: str) -> str | None:
    try:
        acc_resp = httpx.post(f"{TELEGRAPH_API}/createAccount", json={
            "short_name": "BeskromnyAI",
            "author_name": "Бескромный",
            "author_url": "https://t.me/dbeskromny",
        }, timeout=15)
        acc_data = acc_resp.json()
        if not acc_data.get("ok"):
            logger.error("Telegraph account creation failed: %s", acc_data)
            return None

        access_token = acc_data["result"]["access_token"]

        header_nodes = [
            {"tag": "p", "children": [
                {"tag": "em", "children": ["Рабочий бриф для редактора"]},
            ]},
        ]

        content_nodes = _markdown_to_telegraph_nodes(text)
        if not content_nodes:
            logger.error("No content nodes for Telegraph")
            return None

        footer_nodes = [
            {"tag": "hr"},
            {"tag": "p", "children": [
                {"tag": "em", "children": [
                    "Сгенерировано ",
                    {"tag": "a", "attrs": {"href": "https://t.me/dbeskromny"}, "children": ["БескромныйGPT"]},
                ]},
            ]},
        ]

        page_resp = httpx.post(f"{TELEGRAPH_API}/createPage", json={
            "access_token": access_token,
            "title": title,
            "author_name": "Бескромный",
            "author_url": "https://t.me/dbeskromny",
            "content": header_nodes + content_nodes + footer_nodes,
        }, timeout=15)
        page_data = page_resp.json()

        if page_data.get("ok"):
            url = page_data["result"]["url"]
            logger.info("Published to Telegraph: %s", url)
            return url
        else:
            logger.error("Telegraph page creation failed: %s", page_data)
            return None

    except Exception as e:
        logger.error("Telegraph publishing failed: %s", e)
        return None


# ── Main Generator ────────────────────────────────────────────────

def generate_digest() -> tuple[str, str | None]:
    """Gemini generates the full brief from all articles. Publishes to Telegraph."""

    # Step 1: Fetch articles
    logger.info("Fetching articles for digest...")
    articles = fetch_all_articles()
    if not articles:
        return "Не удалось загрузить статьи из источников.", None

    articles_text = _format_articles_for_prompt(articles)
    today = _get_today_msk()

    # Step 2: Gemini generates the full brief
    user_prompt = (
        f"Дата: {today}\n\n"
        f"Ниже — свежие материалы из {len(articles)} источников.\n"
        f"Также учитывай информацию из: {', '.join(TIER2_PAYWALLED_SOURCES)}.\n\n"
        f"МАТЕРИАЛЫ:\n{articles_text}\n\n---\n\n"
        f"Собери рабочий бриф для редактора за {today} строго по структуре из 6 блоков.\n"
        "Для блоков «История дня» и «Дни рождения» — используй свои знания.\n"
        "ВАЖНО: включи 10-12 новостей с балансом (бизнес + технологии + психология + культура/лайфстайл). Не пропускай яркие абсурдные бизнес-кейсы! Больше психологии и социальных трендов.\n"
        "Приоритет при отборе: абсурд и парадокс > цифры > неочевидность.\n"
        "Все ссылки — гиперссылки [текст](url). Никаких хэштегов и декора."
    )

    logger.info("Generating digest via OpenRouter (%s)...", settings.openrouter_digest_model)
    try:
        result = _call_openrouter(DIGEST_SYSTEM, user_prompt)
    except Exception as e:
        logger.error("Digest generation failed: %s", e)
        return f"Ошибка генерации дайджеста: {e}", None

    if not result:
        return "Пустой ответ от модели.", None

    logger.info("Digest generated: %d chars", len(result))

    # Step 3: Publish to Telegraph
    title = f"Бескромный — бриф на {today}"
    telegraph_url = publish_to_telegraph(title, result)

    return result, telegraph_url
