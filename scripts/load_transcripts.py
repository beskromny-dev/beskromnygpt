"""Transcribe and load podcast/interview audio into ChromaDB.

Usage:
    python -m scripts.load_transcripts

Processes audio files in data/transcripts/, runs Whisper,
cleans up hesitations, and indexes into ChromaDB.
"""

# TODO: implement
# 1. Scan data/transcripts/ for audio files
# 2. Transcribe via Whisper locally
# 3. Post-process: remove hesitations, normalize punctuation
# 4. Chunk into semantic segments
# 5. Upsert into ChromaDB with register="conversational"
