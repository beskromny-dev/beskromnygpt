"""RAG retrieval module — semantic search with filters."""

from __future__ import annotations

from typing import Optional

from core.rag.store import get_collection


# Synonym expansion for better recall on Russian queries
SYNONYMS = {
    "монетизация": "монетизация заработок доход реклама деньги на канале рекламный бюджет",
    "ugc": "UGC пользовательский контент user generated content контент от подписчиков аутентичный контент",
    "личный бренд": "личный бренд персональный бренд построение бренда",
    "подписчики": "подписчики аудитория рост канала набор аудитории",
    "контент-план": "контент-план контент-стратегия редакционный план",
    "нейросети": "нейросети ИИ искусственный интеллект AI нейронные сети",
    "выступление": "выступление спикер конференция форум сцена",
    "сторис": "сторис stories истории сториз",
}


def _expand_query(query: str) -> str:
    """Expand query with synonyms for better recall."""
    lower = query.lower()
    expansions = []
    for key, synonyms in SYNONYMS.items():
        if key in lower:
            expansions.append(synonyms)
    if expansions:
        return query + " " + " ".join(expansions)
    return query


def search(
    query: str,
    n_results: int = 5,
    register: Optional[str] = None,
    min_er: Optional[float] = None,
) -> list[dict]:
    """Search ChromaDB for relevant documents.

    Args:
        query: Search query text.
        n_results: Number of results to return.
        register: Filter by register (channel, publicistics, conversational, etc.)
        min_er: Minimum ER score filter.

    Returns:
        List of dicts with keys: text, metadata, distance.
    """
    collection = get_collection()

    where = {}
    if register:
        where["register"] = register
    if min_er is not None:
        where["er_score"] = {"$gte": min_er}

    # ChromaDB needs at least one condition in where, or None
    where_filter = where if where else None

    # Expand query with synonyms
    expanded = _expand_query(query)

    # Fetch extra results so we can filter out short/garbage docs
    fetch_n = n_results * 3

    results = collection.query(
        query_texts=[expanded],
        n_results=fetch_n,
        where=where_filter,
    )

    docs = []
    seen_ids = set()
    for i in range(len(results["ids"][0])):
        text = results["documents"][0][i]
        doc_id = results["ids"][0][i]
        # Skip very short docs (image captions, one-liners)
        if len(text.strip()) < 100:
            continue
        seen_ids.add(doc_id)
        docs.append({
            "id": doc_id,
            "text": text,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
        if len(docs) >= n_results:
            break

    # If most results are weak, try keyword fallback
    weak_count = sum(1 for d in docs[:3] if d.get("distance") and d["distance"] > 0.45)
    if weak_count >= 2:
        _keyword_boost(collection, query, docs, seen_ids, n_results, where_filter)
        # Re-sort: keyword matches get priority if semantic was weak
        docs.sort(key=lambda d: d["distance"] or 0)

    return docs[:n_results]


def _keyword_boost(collection, query: str, docs: list, seen_ids: set, n_results: int, where_filter):
    """Add docs containing query keywords that semantic search missed."""
    keywords = [w for w in query.lower().split() if len(w) > 3]
    if not keywords:
        return

    # Use ChromaDB's where_document filter for keyword search (much faster than full scan)
    for kw in keywords:
        try:
            kw_results = collection.query(
                query_texts=[kw],
                n_results=5,
                where=where_filter,
                where_document={"$contains": kw},
            )
        except Exception:
            continue

        for i in range(len(kw_results["ids"][0])):
            doc_id = kw_results["ids"][0][i]
            text = kw_results["documents"][0][i]
            if doc_id in seen_ids or len(text.strip()) < 100:
                continue
            seen_ids.add(doc_id)
            docs.append({
                "id": doc_id,
                "text": text,
                "metadata": kw_results["metadatas"][0][i],
                "distance": 0.35,  # boost keyword matches
            })
            if len(docs) >= n_results * 2:
                return


def check_duplicates(text: str, threshold: float = 0.15) -> list[dict]:
    """Check if similar content already exists in the archive.

    Args:
        text: Text to check for duplicates.
        threshold: Max distance to consider a duplicate (lower = more similar).

    Returns:
        List of similar documents within threshold.
    """
    results = search(text, n_results=3)
    return [r for r in results if r.get("distance") is not None and r["distance"] < threshold]
