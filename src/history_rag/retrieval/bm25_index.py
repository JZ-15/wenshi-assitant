import logging
import pickle
import re
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

PUNCTUATION = set('，。！？；：、""''（）《》·')

# Default cache path under data/
_DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "bm25_cache.pkl"


def _tokenize(text: str) -> list[str]:
    """Tokenizer for classical Chinese: jieba word segmentation + character-level.

    Combines word-level tokens (to capture multi-char terms like 贞观之治)
    with character-level tokens (since classical Chinese often uses single
    characters as words).
    """
    # Clean whitespace
    text = re.sub(r'[\s\n\r\t]+', '', text)
    # Word-level segmentation via jieba
    words = [w for w in jieba.cut(text) if w not in PUNCTUATION and w.strip()]
    # Character-level tokens as supplement
    chars = [c for c in text if c not in PUNCTUATION]
    return words + chars


class BM25Index:
    """BM25 index built from ChromaDB documents for hybrid search."""

    def __init__(self, collection, cache_path: str | Path | None = _DEFAULT_CACHE_PATH):
        """Build BM25 index from a ChromaDB collection, with disk caching.

        Args:
            collection: A ChromaDB collection instance.
            cache_path: Path to cache file. Set to None to disable caching.
        """
        total = collection.count()
        cache_path = Path(cache_path) if cache_path else None

        # Try loading from cache
        if cache_path and cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("total") == total:
                    self._ids = cached["ids"]
                    self._documents = cached["documents"]
                    self._metadatas = cached["metadatas"]
                    self._index = cached["index"]
                    logger.info("BM25 index loaded from cache (%d documents)", len(self._ids))
                    return
                else:
                    logger.info("Cache stale (cached %d, current %d) — rebuilding", cached.get("total"), total)
            except Exception as e:
                logger.warning("Failed to load BM25 cache: %s — rebuilding", e)

        # Build from scratch
        logger.info("Building BM25 index from ChromaDB collection (%d documents)...", total)

        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict] = []

        batch_size = 5000
        for offset in range(0, total, batch_size):
            batch = collection.get(
                limit=batch_size,
                offset=offset,
                include=["documents", "metadatas"],
            )
            self._ids.extend(batch["ids"])
            self._documents.extend(batch["documents"])
            self._metadatas.extend(batch["metadatas"])

        if not self._ids:
            logger.warning("BM25 index is empty — no documents in collection")
            self._index = None
            return

        # Tokenize documents with source metadata prefix for better keyword matching
        tokenized = []
        for doc, meta in zip(self._documents, self._metadatas):
            prefix = f"{meta.get('citation', '')} {meta.get('chapter', '')} "
            tokenized.append(_tokenize(prefix + doc))
        self._index = BM25Okapi(tokenized)
        logger.info("BM25 index built with %d documents", len(self._ids))

        # Save to cache
        if cache_path:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "wb") as f:
                    pickle.dump({
                        "total": total,
                        "ids": self._ids,
                        "documents": self._documents,
                        "metadatas": self._metadatas,
                        "index": self._index,
                    }, f, protocol=pickle.HIGHEST_PROTOCOL)
                size_mb = cache_path.stat().st_size / (1024 * 1024)
                logger.info("BM25 cache saved to %s (%.1f MB)", cache_path, size_mb)
            except Exception as e:
                logger.warning("Failed to save BM25 cache: %s", e)

    def search(
        self, query: str, top_k: int = 10, source_filter: list[str] | None = None
    ) -> list[dict]:
        """Search the BM25 index.

        Returns results in the same format as VectorStore.query():
        [{"id", "text", "metadata", "distance"}, ...]

        Note: BM25 scores are converted to a pseudo-distance (1 / (1 + score))
        so that lower = more relevant, matching the cosine distance convention.
        """
        if self._index is None or not self._ids:
            return []

        tokenized_query = _tokenize(query)
        scores = self._index.get_scores(tokenized_query)

        # Build (index, score) pairs, optionally filtering by source
        candidates = []
        for i, score in enumerate(scores):
            if score <= 0:
                continue
            if source_filter and self._metadatas[i].get("source") not in source_filter:
                continue
            candidates.append((i, score))

        # Sort by score descending, take top_k
        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:top_k]

        results = []
        for idx, score in candidates:
            results.append({
                "id": self._ids[idx],
                "text": self._documents[idx],
                "metadata": self._metadatas[idx],
                "distance": 1.0 / (1.0 + score),  # Convert to pseudo-distance
            })

        return results
