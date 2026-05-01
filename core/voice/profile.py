"""Voice Profile loader — fetches the profile from Google Docs or local cache."""

from __future__ import annotations

from pathlib import Path

from core.config import DATA_DIR


VOICE_PROFILE_DOC_ID = "1jMRarmpxhVfp5hzPxYuuUdOdxB2d8CXXcMYt9pKLXSo"
LOCAL_CACHE = DATA_DIR / "exports" / "voice_profile_draft.md"


def get_voice_profile() -> str:
    """Return the Voice Profile text.

    For now reads from local cache. Later can fetch from Google Docs.
    """
    if LOCAL_CACHE.exists():
        return LOCAL_CACHE.read_text(encoding="utf-8")
    return ""
