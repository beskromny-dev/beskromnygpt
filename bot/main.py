"""БескромныйGPT Telegram Bot — entry point."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from bot.handlers.commands import (
    post, rewrite, comment, research, article, check, graph, start, style, stats,
    ask, draft, handle_button, handle_awaiting_input,
)
from bot.handlers.feedback import handle_feedback, handle_edit_reply
from bot.handlers.editor import (
    search_archive, recent, queue, view, approve, reject, edit_draft,
    handle_queue_edit_reply, digest,
)
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """Build and return the Telegram bot application."""
    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=120,
        write_timeout=120,
        pool_timeout=30,
    )
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .request(request)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("rewrite", rewrite))
    app.add_handler(CommandHandler("comment", comment))
    app.add_handler(CommandHandler("research", research))
    app.add_handler(CommandHandler("article", article))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("draft", draft))
    app.add_handler(CommandHandler("graph", graph))
    app.add_handler(CommandHandler("style", style))
    app.add_handler(CommandHandler("stats", stats))

    # Editor workflow
    app.add_handler(CommandHandler("search", search_archive))
    app.add_handler(CommandHandler("recent", recent))
    app.add_handler(CommandHandler("queue", queue))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("edit_draft", edit_draft))
    app.add_handler(CommandHandler("digest", digest))

    # Feedback buttons
    app.add_handler(CallbackQueryHandler(handle_feedback, pattern=r"^fb:"))

    # Catch text replies: buttons → awaiting input → queue edits → feedback edits
    async def handle_text_reply(update: Update, context):
        # Russian button presses
        if await handle_button(update, context):
            return
        # Input after button press
        if await handle_awaiting_input(update, context):
            return
        # Queue edit replies
        handled = await handle_queue_edit_reply(update, context)
        if not handled:
            await handle_edit_reply(update, context)

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_reply,
    ))

    return app


if __name__ == "__main__":
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        raise SystemExit(1)

    logger.info("Starting БескромныйGPT bot...")
    create_app().run_polling()
