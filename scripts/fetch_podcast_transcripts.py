"""Download podcast audio, transcribe with Whisper, load into ChromaDB.

Usage:
    python -m scripts.fetch_podcast_transcripts
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

import whisper

from core.config import DATA_DIR
from core.rag.store import get_collection

EXPORTS_DIR = DATA_DIR / "exports"
YTDLP = "/Users/dmitriy/Library/Python/3.9/bin/yt-dlp"

# Podcast URLs from profile
PODCAST_DOMAINS = [
    "mave.digital", "podcast.ru", "podcasts.apple",
    "online-event.megafon", "forbes.ru/podcasts",
]


def download_audio(url: str, output_path: str) -> bool:
    """Download audio from URL using yt-dlp (no ffmpeg needed)."""
    cmd = [
        YTDLP,
        "--no-playlist",
        "-o", output_path,
        "--quiet",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def transcribe_audio(audio_path: str, model) -> str:
    """Transcribe audio file using Whisper."""
    try:
        result = model.transcribe(
            audio_path,
            language="ru",
            verbose=False,
        )
        return result.get("text", "")
    except Exception as e:
        print(f"    Whisper error: {e}")
        return ""


def clean_transcript(text: str) -> str:
    """Clean up transcript text."""
    if not text:
        return ""
    text = re.sub(r'\b(э+м+|а+м+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def main():
    links = json.load(open(EXPORTS_DIR / "profile_links.json", encoding="utf-8"))

    # Filter to podcast URLs
    podcast_links = []
    seen = set()
    for l in links:
        url = l["url"]
        if url in seen:
            continue
        seen.add(url)
        if any(d in url for d in PODCAST_DOMAINS):
            podcast_links.append({"text": l["text"], "url": url})

    print(f"Podcasts to process: {len(podcast_links)}")

    # Load Whisper model (base = good balance of speed/quality for Russian)
    print("Loading Whisper model (base)...")
    model = whisper.load_model("base")
    print("Model loaded.")

    results = []
    for i, p in enumerate(podcast_links, 1):
        url = p["url"]
        title = p["text"]
        print(f"\n  [{i}/{len(podcast_links)}] {title[:60]}...")
        print(f"    URL: {url[:80]}")

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = str(Path(tmpdir) / "audio.mp3")

            # Download audio
            print("    Downloading audio...")
            ok = download_audio(url, audio_path)

            if not ok:
                # Some URLs may need special handling
                # Try direct download for podcast.ru
                if "podcast.ru" in url:
                    print("    Trying podcast.ru page parsing...")
                    ok = download_audio(url, audio_path)

                if not ok:
                    print("    DOWNLOAD FAILED")
                    results.append({
                        "title": title, "url": url,
                        "transcript": "", "error": "download_failed",
                    })
                    continue

            # Check file exists and has content
            audio_file = Path(audio_path)
            if not audio_file.exists():
                # yt-dlp might add extension
                candidates = list(Path(tmpdir).glob("audio*"))
                if candidates:
                    audio_file = candidates[0]
                else:
                    print("    NO AUDIO FILE FOUND")
                    results.append({
                        "title": title, "url": url,
                        "transcript": "", "error": "no_file",
                    })
                    continue

            size_mb = audio_file.stat().st_size / (1024 * 1024)
            print(f"    Audio: {size_mb:.1f} MB")

            # Transcribe
            print("    Transcribing with Whisper...")
            start_time = time.time()
            transcript = transcribe_audio(str(audio_file), model)
            elapsed = time.time() - start_time
            transcript = clean_transcript(transcript)

            if transcript and len(transcript) > 200:
                print(f"    OK: {len(transcript)} chars ({elapsed:.0f}s)")
            else:
                print(f"    TRANSCRIPT TOO SHORT: {len(transcript)} chars")

            results.append({
                "title": title,
                "url": url,
                "transcript": transcript,
                "error": None,
            })

    # Save raw results
    (EXPORTS_DIR / "podcast_transcripts.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Load into ChromaDB
    collection = get_collection()
    loaded = 0

    for r in results:
        text = r.get("transcript", "")
        if len(text) < 200:
            continue

        title = r["title"]
        url = r["url"]

        # Chunk long transcripts
        chunks = []
        if len(text) > 2000:
            words = text.split()
            chunk = []
            chunk_len = 0
            for w in words:
                chunk.append(w)
                chunk_len += len(w) + 1
                if chunk_len > 1500:
                    chunks.append(" ".join(chunk))
                    chunk = []
                    chunk_len = 0
            if chunk:
                chunks.append(" ".join(chunk))
        else:
            chunks = [text]

        for ci, chunk in enumerate(chunks):
            doc_id = f"podcast_{hash(url)}_{ci}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "register": "conversational",
                    "type": "podcast_transcript",
                    "source": url,
                    "title": title[:200],
                    "date": "",
                    "er_score": 0,
                    "time_weight": 1.0,
                }],
            )
            loaded += 1

    ok = len([r for r in results if len(r.get("transcript", "")) >= 200])
    print(f"\nDone. Transcribed {ok}/{len(podcast_links)} podcasts.")
    print(f"Loaded {loaded} chunks into ChromaDB.")
    print(f"Total docs in collection: {collection.count()}")


if __name__ == "__main__":
    main()
