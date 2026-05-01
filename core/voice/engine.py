"""Voice engine — generates text in Dima's voice using RAG + Claude (via OpenRouter)."""

from __future__ import annotations

import httpx

from core.config import settings
from core.rag.retrieval import search, check_duplicates
from core.voice.profile import get_voice_profile
from core.voice.prompts import SYSTEM_PROMPT, COMMAND_PROMPTS

ASK_SYSTEM_PROMPT = """Ты — цифровой мозг Дмитрия Бескромного. У тебя есть доступ к его архиву: 4000+ постов канала, 34 видео-интервью, 6 подкастов, 35 статей в СМИ.

Ниже — фрагменты из архива, релевантные вопросу. Это реальные слова Димы из подкастов, интервью и постов.

КОНТЕКСТ ИЗ АРХИВА:
{rag_context}

ПРАВИЛА:
- Всегда отвечай конкретно и содержательно, опираясь на контекст выше
- Цитируй и пересказывай тезисы Димы — они есть в контексте
- Указывай источник: «в подкасте PR-Агент Купер Дима говорил...», «в посте канала...»
- НЕ говори «в архиве не найдено» — ты получил релевантные фрагменты, работай с ними
- Синтезируй ответ из нескольких источников, если они дополняют друг друга
- Формат: структурированный ответ с тезисами, не простыня текста"""


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _build_rag_context(query: str, register: str = "channel", n: int = 5, max_chars: int = 500) -> str:
    """Retrieve relevant posts and format as context string."""
    results = search(query, n_results=n, register=register)
    if not results:
        return "(архив пуст или не найдено релевантных постов)"

    parts = []
    for r in results:
        m = r["metadata"]
        source_type = m.get("type", "")
        title = m.get("title", "")
        date = m.get("date", "?")

        header = f"[{source_type} | {date}]"
        if title:
            header += f" {title}"

        parts.append(f"{header}\n{r['text'][:max_chars]}")
    return "\n\n---\n\n".join(parts)


def generate(command: str, user_input: str) -> str:
    """Generate text using Voice Profile + RAG + Claude via OpenRouter.

    Args:
        command: One of 'post', 'rewrite', 'comment', 'check', 'research', 'article'.
        user_input: User's input text or topic.

    Returns:
        Generated text in Dima's voice.
    """
    if not settings.openrouter_api_key:
        return (
            "OPENROUTER_API_KEY не настроен.\n\n"
            "Добавь ключ в .env файл:\n"
            "OPENROUTER_API_KEY=sk-or-..."
        )

    # Build RAG context
    register = "channel"
    if command in ("article", "ask", "draft"):
        register = None  # search all registers

    if command == "ask":
        # For brain queries: more results, much longer text per result
        rag_context = _build_rag_context(user_input, register=None, n=10, max_chars=2000)
    elif command == "draft":
        rag_context = _build_rag_context(user_input, register=None, n=5, max_chars=800)
    else:
        rag_context = _build_rag_context(user_input, register=register, n=5, max_chars=500)

    # Build system prompt
    if command == "ask":
        # Use knowledge-base system prompt, not voice generation
        system = ASK_SYSTEM_PROMPT.format(rag_context=rag_context)
    else:
        voice_profile = get_voice_profile()
        rules_start = voice_profile.find("6. ПРАВИЛА ГЕНЕРАЦИИ")
        if rules_start > 0:
            profile_for_prompt = voice_profile[rules_start:]
        else:
            profile_for_prompt = voice_profile[-3000:]

        system = SYSTEM_PROMPT.format(
            voice_profile=profile_for_prompt,
            rag_context=rag_context,
        )

    # Build user prompt
    command_template = COMMAND_PROMPTS.get(command, COMMAND_PROMPTS["post"])
    user_prompt = command_template.format(input=user_input)

    # Special handling for /check
    if command == "check":
        dupes = check_duplicates(user_input)
        if dupes:
            dupe_info = "\n\nПОХОЖИЕ ПОСТЫ ИЗ АРХИВА:\n"
            for d in dupes:
                m = d["metadata"]
                dupe_info += f"\n[{m.get('date', '?')}] (similarity: {1 - d['distance']:.0%})\n{d['text'][:300]}...\n"
            user_prompt += dupe_info
        else:
            user_prompt += "\n\nВ архиве не найдено похожих постов."

    # Call Claude via OpenRouter
    try:
        resp = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://beskromny.ai",
                "X-Title": "BeskromnyAI",
            },
            json={
                "model": settings.openrouter_voice_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 4000,
                "temperature": 0.6,
            },
            timeout=120,
        )
        data = resp.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "error" in data:
            return f"Ошибка API: {data['error'].get('message', data['error'])}"
        else:
            return f"Неожиданный ответ: {data}"

    except Exception as e:
        return f"Ошибка генерации: {e}"
