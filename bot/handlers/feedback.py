"""Feedback button handler — saves user feedback to SQLite."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from core.feedback.db import save_feedback


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard feedback button press."""
    query = update.callback_query
    await query.answer()

    data = query.data  # format: "fb:rating:command"
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "fb":
        return

    rating_map = {"used": "used", "edited": "edited", "rejected": "rejected"}
    rating = rating_map.get(parts[1])
    command = parts[2]

    if not rating:
        return

    # Get stored generation data
    msg_id = query.message.message_id
    gen_data = context.chat_data.get("generations", {}).get(msg_id, {})

    prompt = gen_data.get("prompt", "")
    generated = gen_data.get("generated", query.message.text or "")

    # If edited, wait for the final version before saving
    if rating == "edited":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Отправь финальную версию текста — сохраню пару [сгенерировано → отредактировано] для обучения."
        )
        context.chat_data["awaiting_edit"] = msg_id
        return

    save_feedback(command, prompt, generated, rating)

    label = {"used": "✓ Использовал", "rejected": "✗ Не подошло"}
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Фидбек сохранён: {label.get(rating, rating)}")


async def handle_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the edited version sent after 'edited' feedback."""
    awaiting = context.chat_data.get("awaiting_edit")
    if not awaiting:
        return

    gen_data = context.chat_data.get("generations", {}).get(awaiting, {})
    if gen_data:
        from core.feedback.db import save_feedback
        save_feedback(
            gen_data.get("command", "unknown"),
            gen_data.get("prompt", ""),
            gen_data.get("generated", ""),
            "edited",
            edited=update.message.text,
        )

    context.chat_data.pop("awaiting_edit", None)
    await update.message.reply_text("Пара сохранена. Спасибо за фидбек.")
