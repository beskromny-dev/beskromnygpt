"""Migrate ChromaDB to multilingual embeddings.

Exports all docs from old collection, deletes it, recreates with
new embedding function, and re-imports all docs.

Usage:
    python -m scripts.migrate_embeddings
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from core.config import CHROMA_DIR, DATA_DIR, settings

BATCH_SIZE = 200


def main():
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    old_col = client.get_collection(name=settings.chroma_collection)
    total = old_col.count()
    print(f"Old collection: {total} documents")

    # Export all documents
    print("Exporting...")
    all_data = old_col.get(include=["documents", "metadatas"])
    ids = all_data["ids"]
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]
    print(f"Exported {len(ids)} documents")

    # Save backup
    backup_path = DATA_DIR / "exports" / "chroma_backup.json"
    backup = [{"id": i, "doc": d, "meta": m} for i, d, m in zip(ids, documents, metadatas)]
    backup_path.write_text(json.dumps(backup, ensure_ascii=False), encoding="utf-8")
    print(f"Backup saved to {backup_path}")

    # Delete old collection
    print("Deleting old collection...")
    client.delete_collection(name=settings.chroma_collection)

    # Create new collection with multilingual embeddings
    print("Creating new collection with multilingual embeddings...")
    ef = SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    new_col = client.create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
        embedding_function=ef,
    )

    # Re-import in batches
    print(f"Re-importing {len(ids)} documents in batches of {BATCH_SIZE}...")
    for start in range(0, len(ids), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(ids))
        batch_ids = ids[start:end]
        batch_docs = documents[start:end]
        batch_metas = metadatas[start:end]

        # Filter out empty docs
        valid = [(i, d, m) for i, d, m in zip(batch_ids, batch_docs, batch_metas) if d and len(d.strip()) > 10]
        if not valid:
            continue

        v_ids, v_docs, v_metas = zip(*valid)
        new_col.add(ids=list(v_ids), documents=list(v_docs), metadatas=list(v_metas))
        print(f"  {end}/{len(ids)} ({len(valid)} valid)")

    print(f"\nDone. New collection: {new_col.count()} documents")

    # Quick test
    print("\nTest search: 'личный бренд'")
    results = new_col.query(query_texts=["личный бренд"], n_results=3)
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        print(f"  [{meta.get('type','?')} | dist={dist:.3f}] {doc[:100]}")


if __name__ == "__main__":
    main()
