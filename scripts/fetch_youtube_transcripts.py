"""Fetch YouTube transcripts via yt-dlp and load into ChromaDB.

Usage:
    python -m scripts.fetch_youtube_transcripts
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

from core.config import DATA_DIR
from core.rag.store import get_collection

EXPORTS_DIR = DATA_DIR / "exports"
YTDLP = "/Users/dmitriy/Library/Python/3.9/bin/yt-dlp"


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return ""


def parse_vtt(vtt_text: str) -> str:
    """Extract clean text from VTT subtitle file."""
    lines = vtt_text.split('\n')
    texts = []
    prev = ""
    for line in lines:
        line = line.strip()
        # Skip timestamps, WEBVTT header, empty lines, position info
        if not line or '-->' in line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        # Skip lines that are just numbers (cue identifiers)
        if line.isdigit():
            continue
        # Remove inline timing tags like <00:00:01.000><c>
        line = re.sub(r'<[^>]+>', '', line)
        # Decode HTML entities
        line = line.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
        line = line.strip()
        if not line:
            continue
        # Deduplicate consecutive identical lines (VTT often repeats)
        if line != prev:
            texts.append(line)
            prev = line

    return ' '.join(texts)


def get_transcript_ytdlp(video_id: str) -> str:
    """Fetch transcript using yt-dlp with Chrome cookies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "sub")
        cmd = [
            YTDLP,
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "ru",
            "--skip-download",
            "--no-playlist",
            "--cookies-from-browser", "chrome",
            "-o", output_template,
            "--quiet",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return ""

        # Find downloaded VTT file
        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if not vtt_files:
            return ""

        vtt_text = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
        return parse_vtt(vtt_text)


def clean_transcript(text: str) -> str:
    """Clean up transcript: remove hesitations, normalize."""
    if not text:
        return ""
    # Remove common hesitations
    text = re.sub(r'\b(э+м+|а+м+)\b', '', text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def main():
    links = json.load(open(EXPORTS_DIR / "profile_links.json", encoding="utf-8"))

    # Filter to video URLs
    video_links = []
    seen = set()
    for l in links:
        url = l["url"]
        if url in seen:
            continue
        seen.add(url)
        if any(d in url for d in ["youtube.com", "youtu.be"]):
            vid = extract_video_id(url)
            if vid:
                video_links.append({"text": l["text"], "url": url, "video_id": vid})

    print(f"YouTube videos to process: {len(video_links)}")

    results = []
    for i, v in enumerate(video_links, 1):
        print(f"  [{i}/{len(video_links)}] {v['text'][:60]}...")
        transcript = get_transcript_ytdlp(v["video_id"])
        transcript = clean_transcript(transcript)

        if transcript and len(transcript) > 100:
            print(f"    OK: {len(transcript)} chars")
        else:
            print(f"    NO TRANSCRIPT")

        results.append({
            "title": v["text"],
            "url": v["url"],
            "video_id": v["video_id"],
            "transcript": transcript,
        })
        time.sleep(1)

    # Save raw
    (EXPORTS_DIR / "youtube_transcripts.json").write_text(
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
            doc_id = f"video_{r['video_id']}_{ci}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "register": "conversational",
                    "type": "video_transcript",
                    "source": url,
                    "title": title[:200],
                    "date": "",
                    "er_score": 0,
                    "time_weight": 1.0,
                }],
            )
            loaded += 1

    ok = len([r for r in results if len(r.get("transcript", "")) >= 200])
    print(f"\nDone. Transcribed {ok}/{len(video_links)} videos.")
    print(f"Loaded {loaded} chunks into ChromaDB.")
    print(f"Total docs in collection: {collection.count()}")


if __name__ == "__main__":
    main()
