# БескромныйAI

Персональная голосовая модель и машина полуавтоматизации личного бренда Дмитрия Бескромного.

## Architecture

- **Python backend** — Telegram bot, RAG pipeline, feedback loop
- **Next.js frontend** (`web/`) — public showcase: chat, analytics, economics
- **ChromaDB** — vector store for all content (posts, transcripts, articles)
- **SQLite** — feedback storage (used/edited/rejected per generation)

## Key directories

- `bot/` — Telegram bot (python-telegram-bot)
- `core/rag/` — ChromaDB vector store, embedding, retrieval
- `core/voice/` — Voice Profile logic, prompt construction
- `core/feedback/` — SQLite feedback loop (Block D)
- `core/digest/` — daily digest: scraper, sources config, OpenRouter generator
- `core/queue/` — SQLite content queue (draft → edited → approved → published)
- `scripts/` — data loading scripts (channel archive, transcripts)
- `web/` — Next.js + Tailwind app, deployed to Vercel
- `data/` — local data (ChromaDB, transcripts, SQLite). Not in git.
- `docs/` — internal documentation

## Stack

- Python 3.10+ (server uses system Python 3.10.12, no PPA needed; code uses `from __future__ import annotations` for compatibility)
- **All LLM calls go through OpenRouter** via httpx (no direct Anthropic/Google SDKs):
  - Voice generation, /ask, voice profile rebuild → `anthropic/claude-opus-4.7`
  - Daily digest → `google/gemini-3.1-pro-preview` (fallbacks: `gemini-2.5-pro`, `gemini-2.5-flash`)
  - Single API key (`OPENROUTER_API_KEY`), single billing dashboard, flagship models guaranteed
- **Embeddings: local** multilingual SentenceTransformer (`core/rag/store.py`) — no network, no API key
- ChromaDB, SQLite, python-telegram-bot, Telethon
- Next.js, Tailwind, Recharts, Vercel

## Deployment

- **Production VPS:** `82.22.3.72` (Hostkey NL, mini tier: 4 vCPU / 6 GB RAM / 120 GB SSD, Ubuntu 22.04, hostname `nl-vmmini`, timezone Europe/Moscow). Activated 2026-05-01. Order #40403, panel at https://invapi.hostkey.ru/?id=40403
- **Old VPS** `193.187.95.80` (Hostkey RU): expired 2026-04-30 (forgotten payment), suspended; data may be recoverable during grace period via Hostkey support.
- **SSH:** `ssh root@82.22.3.72` (key-only via `~/.ssh/id_ed25519`, password auth disabled in `sshd_config`). Emergency root password kept by user only (for VNC console use); rotated from Hostkey-issued one on first login.
- **Project root on server:** `/root/beskromny/`, venv at `/root/beskromny/venv/`.
- **Swap:** 4 GB at `/swapfile` (swappiness=10) — insurance against OOM during digest peaks.
- **systemd service:** `beskromny-bot.service` — `python -m bot.main`, auto-restart on failure (RestartSec=10).
- **cron jobs (all in MSK, server TZ=Europe/Moscow):**
  - `0 6 * * *` — daily digest via `python -m scripts.generate_digest`
  - `0 4 * * *` — data backup via `scripts/backup_data.sh` (feedback.db, queue.db, chroma tarball → `/root/backups/`, 30-day retention)
  - `0 9 * * 1` — weekly Hostkey payment reminder via `scripts/payment_reminder.sh` (Telegram alert to OWNER_ID; **set up after the previous server lapsed**)
- **Logs:** `/var/log/beskromny-digest.log`, `/var/log/beskromny-backup.log`; rotated weekly via logrotate (`/etc/logrotate.d/beskromny`, 8-week retention, copytruncate).
- **Deploy:** `rsync` project files (excluding `.git`, `data/`, `.env`, `venv/`, `web/node_modules/`), then `systemctl restart beskromny-bot`.

## Backup & version control

- **GitHub repo** (private): https://github.com/beskromny-dev/beskromnygpt.git — initial push deferred until after new VPS validates working state (digest + bot run successfully end-to-end).
- `data/` is **never versioned** — regenerate via `scripts/fetch_*.py` and `scripts/load_*.py`. Add `data/` to `.gitignore` before first push (currently only `data/chroma/` is excluded).
- Local data backup convention: `~/Desktop/beskromny_data_backup_<YYYY-MM-DD>.zip` containing full `data/` dir (chroma, exports, SQLite DBs). Latest snapshot: `2026-05-01` (59 MB).
- `feedback.db` and `queue.db` are irreplaceable (no source to regenerate from) — always include in local backups.

## Commands

- `python -m bot.main` — run Telegram bot
- `python -m scripts.generate_digest` — generate and send digest (PDF + summary)
- `python -m scripts.generate_digest --dry` — dry run (print only)
- `python -m scripts.generate_digest --test` — send to owner only with [ТЕСТ] marker
- `python -m scripts.load_channel_archive` — load channel posts into ChromaDB
- `python -m scripts.load_transcripts` — transcribe and load audio into ChromaDB

## Digest pipeline

- 41 RSS sources (Tier 1): 12 intl media + 14 thought leaders + 15 Russian
- Tier 2: 11 Google CSE search queries (paywalled sources)
- Generator: `google/gemini-3.1-pro-preview` via OpenRouter, with retry-on-503 + fallback chain to `google/gemini-2.5-pro`, `google/gemini-2.5-flash` (`core/digest/generator.py`)
- Delivery: curated Telegram summary (text) + full PDF attachment (`core/digest/pdf.py`, weasyprint)
- Telegraph link kept as optional browser view
- PDF requires libpango on server: `apt install -y libpango-1.0-0 libpangoft2-1.0-0`
- Sources config: `core/digest/sources.py`
- Reliability: Telegram sendMessage/sendDocument have 4x exponential-backoff retries; top-level `_run()` wraps `main()` and sends `⚠️` alerts to owner on any failure (`core/digest/alerts.py`)
- Summary parser accepts both `## Выжимка для Telegram` header and plain «Доброе утро» greeting (the model sometimes drops the header)

## Content registers

Every document in ChromaDB has a `register` metadata field:
channel | publicistics | conversational | speeches | saved | work

## Conventions

- All user-facing text in Russian
- Code and comments in English
- Use ruff for linting (`ruff check .`)
- Config via .env file, accessed through `core.config.settings`
