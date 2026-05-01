"""Telegram bot command handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from core.voice.engine import generate
from core.voice.profile import get_voice_profile
from core.rag.store import get_collection
from core.config import settings

TG_MSG_LIMIT = 4096

# Only these commands get feedback buttons (for voice model training)
_FEEDBACK_COMMANDS = {"post", "rewrite"}


def _feedback_keyboard(command: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Использовал", callback_data=f"fb:used:{command}"),
            InlineKeyboardButton("✎ Отредактировал", callback_data=f"fb:edited:{command}"),
            InlineKeyboardButton("✗ Не подошло", callback_data=f"fb:rejected:{command}"),
        ]
    ])


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Написать пост"), KeyboardButton("Рерайт")],
        [KeyboardButton("Спросить мозг"), KeyboardButton("Комментарий")],
        [KeyboardButton("Ресёрч"), KeyboardButton("Аналитика")],
        [KeyboardButton("Очередь")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Нажми кнопку или напиши команду...",
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "БескромныйGPT на связи.\n\n"
        "СОЗДАТЬ КОНТЕНТ:\n"
        "/post [тема] — пост для канала с нуля\n"
        "/draft [мысли] — из сырых заметок в пост\n"
        "/rewrite [текст] — рерайт в голосе Димы\n"
        "/comment [текст] — 2-3 варианта комментария\n"
        "/article [тема] — черновик статьи (Forbes/РБК)\n"
        "/research [тема] — анализ темы + черновик\n\n"
        "ИНСТРУМЕНТЫ:\n"
        "/ask [вопрос] — спросить про Диму и его позиции\n"
        "/check [тезис] — проверка повторов в архиве\n"
        "/digest — сгенерировать дайджест прямо сейчас\n\n"
        "РЕДАКТУРА:\n"
        "/queue — очередь черновиков\n"
        "/view [id] — посмотреть черновик\n"
        "/approve [id] — одобрить\n"
        "/reject [id] — отклонить\n"
        "/edit_draft [id] — редактировать черновик\n\n"
        "ПРОЧЕЕ:\n"
        "/stats — статистика и аналитика\n"
        "/style — Voice Profile (краткая версия)",
        reply_markup=MAIN_KEYBOARD,
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    prompts = {
        "Написать пост": ("post", "Напиши тему или скинь сырые мысли — разберусь:"),
        "Спросить мозг": ("ask", "Задай вопрос:"),
        "Рерайт": ("rewrite", "Скинь текст, который нужно переписать:"),
        "Комментарий": ("comment", "Скинь текст, на который нужен комментарий:"),
        "Ресёрч": ("research", "Тема для исследования:"),
    }

    if text == "Очередь":
        from bot.handlers.editor import queue
        await queue(update, context)
        return True

    if text == "Аналитика":
        await stats(update, context)
        return True

    if text in prompts:
        cmd, prompt_text = prompts[text]
        context.chat_data["awaiting_command"] = cmd
        await update.message.reply_text(prompt_text)
        return True

    return False


async def handle_awaiting_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    cmd = context.chat_data.get("awaiting_command")
    if not cmd:
        return False

    context.chat_data.pop("awaiting_command", None)
    context.args = update.message.text.split()
    await _generate_and_reply(update, context, cmd)
    return True


async def _generate_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
):
    user_id = update.effective_user.id
    if not settings.is_authorized(user_id):
        await update.message.reply_text(
            f"Нет доступа. Твой Telegram ID: {user_id}\n"
            "Попроси владельца добавить тебя в EDITOR_IDS."
        )
        return

    user_input = " ".join(context.args) if context.args else ""
    if not user_input:
        await update.message.reply_text(f"Укажи тему или текст после /{command}")
        return

    await update.message.chat.send_action("typing")

    try:
        result = generate(command, user_input)
    except Exception as e:
        await update.message.reply_text(f"Ошибка генерации: {e}")
        return

    if not result:
        await update.message.reply_text("Пустой ответ от модели. Попробуй ещё раз.")
        return

    show_feedback = command in _FEEDBACK_COMMANDS

    if not show_feedback:
        await _send_chunks(update, result)
        return

    # Post/rewrite: show feedback buttons for training data
    if not context.chat_data.get("generations"):
        context.chat_data["generations"] = {}

    chunks = _split_text(result)
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        msg = await update.message.reply_text(
            chunk,
            reply_markup=_feedback_keyboard(command) if is_last else None,
            read_timeout=60,
            write_timeout=60,
        )
    context.chat_data["generations"][msg.message_id] = {
        "command": command,
        "prompt": user_input,
        "generated": "\n".join(chunks),
    }


def _split_text(text: str) -> list[str]:
    chunks = []
    while text:
        if len(text) <= TG_MSG_LIMIT:
            chunks.append(text)
            break
        split = text.rfind("\n", 0, TG_MSG_LIMIT)
        if split < TG_MSG_LIMIT // 2:
            split = TG_MSG_LIMIT
        chunks.append(text[:split])
        text = text[split:].lstrip("\n")
    return chunks


async def _send_chunks(update: Update, text: str):
    for chunk in _split_text(text):
        await update.message.reply_text(chunk, read_timeout=60, write_timeout=60)


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "post")

async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "rewrite")

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "comment")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "check")

async def research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "research")

async def article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "article")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "ask")

async def draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _generate_and_reply(update, context, "draft")


async def style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = get_voice_profile()
    if not profile:
        await update.message.reply_text("Voice Profile не найден.")
        return

    lines = profile.split("\n")
    summary_parts = []
    for i, line in enumerate(lines):
        if "ЛИНГВИСТИЧЕСКИЕ" in line.upper():
            summary_parts.append("\n".join(lines[i:i+15]).strip())
        elif "СТРУКТУРНЫЕ" in line.upper() and "ПАТТЕРН" in line.upper():
            summary_parts.append("\n".join(lines[i:i+10]).strip())
        elif "ПРАВИЛА ГЕНЕРАЦИИ" in line.upper():
            summary_parts.append("\n".join(lines[i:i+20]).strip())

    if not summary_parts:
        summary_parts = [profile[:2000]]

    text = "VOICE PROFILE (краткая версия)\n\n" + "\n\n---\n\n".join(summary_parts)
    if len(text) > TG_MSG_LIMIT:
        text = text[:TG_MSG_LIMIT - 50] + "\n\n... (полная версия в Google Docs)"
    await update.message.reply_text(text)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show LiveDune channel analytics."""
    await update.message.chat.send_action("typing")
    try:
        from core.analytics.livedune import get_channel_stats, get_top_posts, get_growth_data
        from core.analytics.formatter import format_channel_report
        stats_data = await get_channel_stats()
        top = await get_top_posts(limit=5)
        growth = await get_growth_data()
        report = format_channel_report(stats_data, top, growth)
        await update.message.reply_text(report)
    except Exception as e:
        await update.message.reply_text(
            "Аналитика канала временно недоступна.\n"
            f"LiveDune не отвечает: {e}"
        )


async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stats(update, context)
