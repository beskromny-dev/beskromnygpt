"""Centralized configuration for БескромныйGPT."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"


class Settings(BaseSettings):
    # OpenRouter — unified provider for ALL LLM calls
    openrouter_api_key: str = ""
    openrouter_voice_model: str = "anthropic/claude-opus-4.7"  # posts, /ask, voice profile rebuild
    openrouter_digest_model: str = "google/gemini-3.1-pro-preview"  # daily digest

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    # Telegram Userbot
    telegram_api_id: Optional[int] = None
    telegram_api_hash: str = ""

    # LiveDune
    livedune_api_key: str = ""

    # T-Bank
    tbank_api_token: str = ""

    # Search APIs (for digest Tier 2)
    brave_search_api_key: str = ""
    google_cse_api_key: str = ""
    google_cse_cx: str = ""

    # ChromaDB
    chroma_collection: str = "beskromny_main"

    # Access control
    owner_id: int = 0  # Telegram user ID of the owner (Dmitriy)
    editor_ids: str = ""  # Comma-separated Telegram user IDs of editors

    @property
    def editor_id_list(self) -> list[int]:
        """Parse EDITOR_IDS string into a list of ints."""
        if not self.editor_ids:
            return []
        return [int(x.strip()) for x in self.editor_ids.split(",") if x.strip()]

    def is_owner(self, user_id: int) -> bool:
        return self.owner_id == user_id

    def is_editor(self, user_id: int) -> bool:
        return user_id in self.editor_id_list

    def is_authorized(self, user_id: int) -> bool:
        return self.is_owner(user_id) or self.is_editor(user_id)

    model_config = {
        "env_file": str(ROOT_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # tolerate legacy env vars from old .env files
    }


settings = Settings()
