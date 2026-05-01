"""ChromaDB vector store for content memory (Block A)."""

from __future__ import annotations

from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from core.config import CHROMA_DIR, settings

# Multilingual embeddings — critical for Russian content
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def get_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client."""
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection(client: Optional[chromadb.ClientAPI] = None) -> chromadb.Collection:
    """Get or create the main collection with multilingual embeddings."""
    if client is None:
        client = get_client()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
        embedding_function=_embedding_fn,
    )
