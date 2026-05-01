"""Send failure notifications to the owner's Telegram chat when the digest pipeline breaks."""

from __future__ import annotations

import logging
import traceback

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


def notify_owner(message: str, error: BaseException | None = None) -> bool:
    """Send a short alert to the owner. Best-effort: never raises."""
    if not settings.telegram_bot_token or not settings.owner_id:
        logger.error("Cannot notify owner: TELEGRAM_BOT_TOKEN or OWNER_ID missing")
        return False

    body = f"⚠️ БескромныйGPT: {message}"
    if error is not None:
        tb = "".join(traceback.format_exception_only(type(error), error)).strip()
        body += f"\n\n{tb[:500]}"

    body = body[:3800]

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        resp = httpx.post(
            url,
            json={"chat_id": settings.owner_id, "text": body, "disable_web_page_preview": True},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error("Alert delivery failed: %s", resp.text)
            return False
        return True
    except Exception as e:
        logger.error("Alert delivery exception: %s", e)
        return False
