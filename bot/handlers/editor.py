"""Editor workflow handlers — search, queue, approve, recent."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from datetime import datetime, timezone

from core.config import settings
from core.rag.retrieval import search as rag_search
from core.rag.store import get_collection
from core.queue.db import add_to_queue, get_queue, get_item, update_status, save_edit


# ── Access helpers ──────────────────────────────────────────────────

def _user_id(update: Update) -> int:
    return update.effective_user.id


async def _require_auth(update: Update) -> bool:
    """Check if user is authorized. Sends a message and returns False if not."""
    uid = _user_id(update)
    if settings.is_authorized(uid):
        return True
    await update.message.reply_text(
        f"Нет доступа. Твой Telegram ID: {uid}\n"
        "Попроси владельца добавить тебя в EDITOR_IDS."
    )
    return False


async def _require_owner(update: Update) -> bool:
    """Check if user is the owner."""
    uid = _user_id(update)
    if settings.is_owner(uid):
        return True
    await update.message.reply_text("Эта команда доступна только владельцу.")
    return False


# ── /search [запрос] ───────────────────────────────────────────────

async def search_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the content archive by topic."""
    if not await _require_auth(update):
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Укажи тему: /search [запрос]")
        return

    await update.message.chat.send_action("typing")

    results = rag_search(query, n_results=7)
    if not results:
        await update.message.reply_text("Ничего не найдено по запросу.")
        return

    lines = [f"ПОИСК ПО АРХИВУ: «{query}»\n"]
    for i, r in enumerate(results, 1):
        m = r["metadata"]
        date = m.get("date", "?")
        register = m.get("register", "?")
        er = m.get("er_score", "")
        er_str = f" | ER={er}%" if er else ""

        snippet = r["text"][:300].replace("\n", " ")
        if len(r["text"]) > 300:
            snippet += "..."

        similarity = f"{(1 - r['distance']) * 100:.0f}%" if r.get("distance") is not None else "?"

        lines.append(f"{i}. [{date} | {register}{er_str}] (релевантность: {similarity})")
        lines.append(f"   {snippet}\n")

    text = "\n".join(lines)
    if len(text) > 4096:
        text = text[:4050] + "\n\n... (показаны не все результаты)"

    await update.message.reply_text(text)


# ── /recent ────────────────────────────────────────────────────────

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent posts from the channel archive."""
    if not await _require_auth(update):
        return

    await update.message.chat.send_action("typing")

    try:
        collection = get_collection()
        results = collection.get(
            where={"register": "channel"},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка доступа к архиву: {e}")
        return

    if not results["ids"]:
        await update.message.reply_text("Архив канала пуст.")
        return

    # Sort by date descending
    items = list(zip(results["documents"], results["metadatas"]))
    items.sort(key=lambda x: x[1].get("date", ""), reverse=True)
    items = items[:10]

    lines = ["ПОСЛЕДНИЕ 10 ПОСТОВ В КАНАЛЕ\n"]
    for i, (text, meta) in enumerate(items, 1):
        date = meta.get("date", "?")
        er = meta.get("er_score", "")
        er_str = f" | ER={er}%" if er else ""

        snippet = text[:200].replace("\n", " ")
        if len(text) > 200:
            snippet += "..."

        lines.append(f"{i}. [{date}{er_str}]")
        lines.append(f"   {snippet}\n")

    text = "\n".join(lines)
    if len(text) > 4096:
        text = text[:4050] + "\n..."

    await update.message.reply_text(text)


# ── /queue [status] ───────────────────────────────────────────────

async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the content queue. Optional filter: /queue edited"""
    if not await _require_auth(update):
        return

    status_filter = context.args[0] if context.args else None
    valid = {"draft", "edited", "approved", "rejected", "published"}
    if status_filter and status_filter not in valid:
        await update.message.reply_text(
            f"Фильтр статуса: {', '.join(sorted(valid))}\n"
            "Пример: /queue edited"
        )
        return

    items = get_queue(status=status_filter, limit=15)
    if not items:
        label = f" (статус: {status_filter})" if status_filter else ""
        await update.message.reply_text(f"Очередь пуста{label}.")
        return

    status_emoji = {
        "draft": "📝",
        "edited": "✏️",
        "approved": "✅",
        "rejected": "❌",
        "published": "📢",
    }

    lines = ["ОЧЕРЕДЬ КОНТЕНТА\n"]
    for item in items:
        emoji = status_emoji.get(item["status"], "•")
        topic = item["topic"] or "(без темы)"
        date = item["created_at"][:10]
        text_preview = (item.get("edited") or item["generated"])[:80].replace("\n", " ")

        lines.append(f"{emoji} #{item['id']} [{date}] /{item['command']} — {topic}")
        lines.append(f"   {text_preview}...")
        lines.append("")

    text = "\n".join(lines)
    text += "\nКоманды: /view [id] | /approve [id] | /reject [id] | /edit_draft [id]"

    if len(text) > 4096:
        text = text[:4050] + "\n..."

    await update.message.reply_text(text)


# ── /view [id] ────────────────────────────────────────────────────

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View full text of a queue item."""
    if not await _require_auth(update):
        return

    if not context.args:
        await update.message.reply_text("Укажи номер: /view [id]")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return

    item = get_item(item_id)
    if not item:
        await update.message.reply_text(f"Элемент #{item_id} не найден.")
        return

    status_label = item["status"].upper()
    topic = item["topic"] or "(без темы)"
    text = f"#{item['id']} | {status_label} | /{item['command']} — {topic}\n"
    text += f"Создано: {item['created_at'][:16]}\n\n"

    if item.get("edited"):
        text += "ОТРЕДАКТИРОВАННАЯ ВЕРСИЯ:\n\n"
        text += item["edited"]
        text += "\n\n---\nОРИГИНАЛ:\n\n"
        text += item["generated"]
    else:
        text += item["generated"]

    if item.get("reviewer_note"):
        text += f"\n\n💬 Комментарий: {item['reviewer_note']}"

    # Split if too long
    if len(text) <= 4096:
        await update.message.reply_text(text)
    else:
        chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
        for chunk in chunks:
            await update.message.reply_text(chunk)


# ── /approve [id] [комментарий] ──────────────────────────────────

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a draft (owner only)."""
    if not await _require_owner(update):
        return

    if not context.args:
        await update.message.reply_text("Укажи номер: /approve [id] [комментарий]")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return

    note = " ".join(context.args[1:]) if len(context.args) > 1 else None

    if update_status(item_id, "approved", reviewer_note=note):
        await update.message.reply_text(f"✅ #{item_id} одобрен.")
    else:
        await update.message.reply_text(f"Элемент #{item_id} не найден.")


# ── /reject [id] [причина] ───────────────────────────────────────

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a draft (owner only)."""
    if not await _require_owner(update):
        return

    if not context.args:
        await update.message.reply_text("Укажи номер: /reject [id] [причина]")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return

    note = " ".join(context.args[1:]) if len(context.args) > 1 else None

    if update_status(item_id, "rejected", reviewer_note=note):
        await update.message.reply_text(f"❌ #{item_id} отклонён.")
    else:
        await update.message.reply_text(f"Элемент #{item_id} не найден.")


# ── /edit_draft [id] ─────────────────────────────────────────────

async def edit_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start editing a draft. Next message will be saved as the edited version."""
    if not await _require_auth(update):
        return

    if not context.args:
        await update.message.reply_text("Укажи номер: /edit_draft [id]")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return

    item = get_item(item_id)
    if not item:
        await update.message.reply_text(f"Элемент #{item_id} не найден.")
        return

    if item["status"] not in ("draft", "edited"):
        await update.message.reply_text(
            f"#{item_id} в статусе «{item['status']}» — редактировать можно только черновики."
        )
        return

    context.chat_data["awaiting_queue_edit"] = item_id
    await update.message.reply_text(
        f"Редактирование #{item_id}.\n"
        "Отправь отредактированную версию текста следующим сообщением."
    )


async def handle_queue_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle edited text for a queue item. Returns True if handled."""
    item_id = context.chat_data.get("awaiting_queue_edit")
    if not item_id:
        return False

    if save_edit(item_id, update.message.text):
        await update.message.reply_text(
            f"✏️ #{item_id} обновлён. Статус: edited.\n"
            "Ждёт одобрения владельца (/approve)."
        )
    else:
        await update.message.reply_text(f"Ошибка: элемент #{item_id} не найден.")

    context.chat_data.pop("awaiting_queue_edit", None)
    return True


# ── /digest ───────────────────────────────────────────────────────

async def digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate daily digest on demand."""
    if not await _require_auth(update):
        return

    await update.message.reply_text(
        "Генерирую дайджест... Это займёт 1-3 минуты."
    )
    await update.message.chat.send_action("typing")

    try:
        from core.digest.generator import generate_digest
        result, telegraph_url = generate_digest()
    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации дайджеста: {e}")
        return

    if not result:
        await update.message.reply_text("Пустой результат. Попробуй позже.")
        return

    # Save to queue
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    queue_id = add_to_queue(
        author_id=_user_id(update),
        command="digest",
        topic=f"дайджест {today} (ручной)",
        generated=result,
    )

    # Send Telegraph link + teaser, or full text as fallback
    if telegraph_url:
        teaser_lines = []
        for line in result.split("\n"):
            teaser_lines.append(line)
            if line.strip().endswith("Поехали.") or len(teaser_lines) > 8:
                break
        teaser = "\n".join(teaser_lines)
        await update.message.reply_text(
            f"{teaser}\n\nЧитать полный дайджест: {telegraph_url}\n\n"
            f"Сохранён в очередь: #{queue_id}"
        )
    else:
        # Fallback: send full text
        if len(result) <= 4096:
            await update.message.reply_text(result)
        else:
            chunks = []
            text = result
            while text:
                if len(text) <= 4096:
                    chunks.append(text)
                    break
                split = text.rfind("\n", 0, 4096)
                if split < 2000:
                    split = 4096
                chunks.append(text[:split])
                text = text[split:].lstrip("\n")
            for chunk in chunks:
                await update.message.reply_text(chunk)
        await update.message.reply_text(f"Дайджест сохранён в очередь: #{queue_id}")
