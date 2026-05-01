"""Generate and send daily digest to Telegram (PDF + short summary message).

Usage:
    python -m scripts.generate_digest          # generate and send to owner
    python -m scripts.generate_digest --dry    # generate and print (no send)
    python -m scripts.generate_digest --test   # send to owner with [TEST] marker

Cron example (every day at 06:00 Moscow / 03:00 UTC):
    0 3 * * * cd /path/to/БескромныйGPT && python -m scripts.generate_digest
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

from core.config import settings
from core.digest.alerts import notify_owner
from core.digest.generator import generate_digest
from core.digest.pdf import render_digest_pdf
from core.queue.db import add_to_queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

TG_MSG_LIMIT = 4096
MSK = timezone(timedelta(hours=3))


def _today_labels() -> tuple[str, str]:
    now = datetime.now(MSK)
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    ru_date = f"{now.day} {months[now.month - 1]} {now.year}"
    iso_date = now.strftime("%Y-%m-%d")
    return ru_date, iso_date


SUMMARY_HEADER_RE = re.compile(r"^##\s*Выжимка\s+для\s+Telegram\s*$", re.IGNORECASE | re.MULTILINE)
SUMMARY_GREETING_RE = re.compile(r"Доброе\s+утро", re.IGNORECASE)


def _clean_summary(text: str) -> str:
    text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE).strip()
    return text


def _clean_body(text: str) -> str:
    text = re.sub(r"\n---\s*\n---\s*\n", "\n---\n", text).strip()
    while text.startswith("---"):
        text = text[3:].lstrip()
    return text.strip()


def split_summary_and_body(full_text: str) -> tuple[str, str]:
    """Pull out the Telegram summary; return (summary, body_without_summary).

    Accepts two shapes from Gemini:
    1. Explicit '## Выжимка для Telegram' header
    2. No header — summary starts with «Доброе утро» and ends at first '## ' block
    """
    m = SUMMARY_HEADER_RE.search(full_text)
    if m:
        start = m.end()
        next_h2 = re.search(r"^##\s+", full_text[start:], re.MULTILINE)
        end = start + next_h2.start() if next_h2 else len(full_text)
        summary = _clean_summary(full_text[start:end])
        body = _clean_body(full_text[:m.start()] + full_text[end:])
        return summary, body

    greet = SUMMARY_GREETING_RE.search(full_text)
    next_h2 = re.search(r"^##\s+", full_text, re.MULTILINE)
    if greet and next_h2 and greet.start() < next_h2.start():
        summary = _clean_summary(full_text[greet.start():next_h2.start()])
        body = _clean_body(full_text[next_h2.start():])
        logger.info("Summary extracted via greeting fallback")
        return summary, body

    logger.warning("Summary block not found — PDF will contain everything, short fallback used")
    return "", full_text


TG_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


async def _post_with_retry(client: httpx.AsyncClient, url: str, *, attempts: int = 4, **kwargs) -> httpx.Response | None:
    """POST with retry on transient errors. Returns last response, or None on total failure."""
    last_resp = None
    for i in range(attempts):
        try:
            resp = await client.post(url, **kwargs)
            last_resp = resp
            if resp.status_code == 200:
                return resp
            if resp.status_code not in TG_RETRY_STATUSES:
                # Permanent error (400, 401, 403, etc.)
                logger.error("Telegram permanent error %d: %s", resp.status_code, resp.text[:200])
                return resp
            wait = 2 ** i
            logger.warning("Telegram %d — retry %d/%d in %ds", resp.status_code, i + 1, attempts, wait)
            await asyncio.sleep(wait)
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            wait = 2 ** i
            logger.warning("Telegram HTTP error: %s — retry %d/%d in %ds", e, i + 1, attempts, wait)
            await asyncio.sleep(wait)
    return last_resp


async def send_text(text: str, chat_id: int) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= TG_MSG_LIMIT:
            chunks.append(remaining)
            break
        split = remaining.rfind("\n", 0, TG_MSG_LIMIT)
        if split < TG_MSG_LIMIT // 2:
            split = TG_MSG_LIMIT
        chunks.append(remaining[:split])
        remaining = remaining[split:].lstrip("\n")

    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            resp = await _post_with_retry(client, url, json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            })
            if resp is None or resp.status_code != 200:
                logger.error("sendMessage failed permanently for chat %d", chat_id)
                return False
    return True


async def send_document(pdf_path: Path, chat_id: int, caption: str = "") -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendDocument"
    async with httpx.AsyncClient(timeout=90) as client:
        for attempt in range(4):
            try:
                with open(pdf_path, "rb") as f:
                    files = {"document": (pdf_path.name, f, "application/pdf")}
                    data = {"chat_id": str(chat_id)}
                    if caption:
                        data["caption"] = caption[:1024]
                    resp = await client.post(url, data=data, files=files)
                if resp.status_code == 200:
                    return True
                if resp.status_code not in TG_RETRY_STATUSES:
                    logger.error("sendDocument permanent error %d: %s", resp.status_code, resp.text[:200])
                    return False
                wait = 2 ** attempt
                logger.warning("sendDocument %d — retry %d/4 in %ds", resp.status_code, attempt + 1, wait)
                await asyncio.sleep(wait)
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                wait = 2 ** attempt
                logger.warning("sendDocument HTTP error: %s — retry %d/4 in %ds", e, attempt + 1, wait)
                await asyncio.sleep(wait)
    logger.error("sendDocument failed permanently for chat %d", chat_id)
    return False


async def deliver(summary: str, pdf_path: Path, telegraph_url: str | None, chat_id: int) -> bool:
    message = summary
    if telegraph_url:
        message = f"{summary}\n\nВ браузере: {telegraph_url}"
    ok_msg = await send_text(message, chat_id)
    ok_pdf = await send_document(pdf_path, chat_id)
    return ok_msg and ok_pdf


async def main():
    dry_run = "--dry" in sys.argv
    test_run = "--test" in sys.argv

    logger.info("Generating daily digest...")
    try:
        digest, telegraph_url = generate_digest()
    except Exception as e:
        logger.exception("Digest generation raised")
        if not dry_run:
            notify_owner("Дайджест не сгенерировался — Gemini упал даже после fallback-моделей.", e)
        sys.exit(1)

    if not digest or digest.startswith("Ошибка") or digest.startswith("Не удалось"):
        logger.error("Digest generation failed: %s", digest[:200])
        if not dry_run:
            notify_owner(f"Дайджест не сгенерировался: {digest[:300]}")
        sys.exit(1)

    logger.info("Digest generated: %d chars", len(digest))
    if telegraph_url:
        logger.info("Telegraph URL: %s", telegraph_url)

    summary, body = split_summary_and_body(digest)
    if not summary:
        summary = (
            "Доброе утро, Дима! Дайджест готов — детали в PDF."
        )

    ru_date, iso_date = _today_labels()
    if test_run:
        summary = f"[ТЕСТ] {summary}"

    # Render PDF
    pdf_dir = Path("data/digests")
    pdf_path = pdf_dir / f"beskromny_digest_{iso_date}.pdf"
    try:
        render_digest_pdf(body, ru_date, pdf_path)
    except Exception as e:
        logger.exception("PDF rendering failed")
        if not dry_run:
            notify_owner("PDF не отрендерился — дайджест уйдёт текстом.", e)
        pdf_path = None

    # Save body to queue (PDF version, not the summary)
    owner_id = settings.owner_id or 0
    queue_id = add_to_queue(
        author_id=owner_id,
        command="digest",
        topic=f"daily digest {iso_date}",
        generated=digest,
    )
    logger.info("Saved to queue as #%d", queue_id)

    if dry_run:
        print("\n" + "=" * 60)
        print("TELEGRAM SUMMARY:\n")
        print(summary)
        print("\n" + "=" * 60)
        print("PDF BODY:\n")
        print(body[:2000] + ("..." if len(body) > 2000 else ""))
        print("=" * 60)
        if telegraph_url:
            print(f"\nTelegraph: {telegraph_url}")
        if pdf_path:
            print(f"PDF saved to: {pdf_path}")
        print(f"Saved to queue as #{queue_id}. Dry run — not sent to Telegram.")
        return

    if not settings.owner_id:
        logger.error("OWNER_ID not set — cannot send digest")
        print(digest)
        return

    if not pdf_path:
        # PDF failed — fallback to text-only teaser + telegraph link
        fallback = summary
        if telegraph_url:
            fallback += f"\n\nЧитать полный дайджест: {telegraph_url}"
        await send_text(fallback, settings.owner_id)
        return

    failed_recipients: list[str] = []

    ok = await deliver(summary, pdf_path, telegraph_url, settings.owner_id)
    if ok:
        logger.info("Digest sent to owner (ID: %d)", settings.owner_id)
    else:
        logger.error("Failed to send digest to owner")
        failed_recipients.append(f"owner {settings.owner_id}")

    if not test_run:
        for editor_id in settings.editor_id_list:
            ok = await deliver(summary, pdf_path, telegraph_url, editor_id)
            if ok:
                logger.info("Digest sent to editor (ID: %d)", editor_id)
            else:
                failed_recipients.append(f"editor {editor_id}")

    if failed_recipients:
        notify_owner(
            f"Дайджест доставлен частично. Не получили: {', '.join(failed_recipients)}"
        )


def _run():
    try:
        asyncio.run(main())
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in digest pipeline")
        if "--dry" not in sys.argv:
            notify_owner("Дайджест упал с необработанной ошибкой.", e)
        sys.exit(1)


if __name__ == "__main__":
    _run()
