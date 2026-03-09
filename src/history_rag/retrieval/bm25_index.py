import logging
import re

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer for classical Chinese: character-level + punctuation split.

    Classical Chinese has no spaces, so character-level tokenization is a
    reasonable baseline. Punctuation is removed.
    """
    # Remove punctuation and whitespace
    text = re.sub(r'[，。！？；：、""''（）《》\s\n\r\t]', '', text)
    return list(text)


class BM25Index:
    """BM25 index built from ChromaDB documents for hybrid search."""

    def __init__(self, collection):
        """Build BM25 index from a ChromaDB collection.

        Args:
            collection: A ChromaDB collection instance.
        """
        logger.info("Building BM25 index from ChromaDB collection...")

        # Load all documents in batches to avoid ChromaDB SQL variable limits
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict] = []

        total = collection.count()
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

        # Tokenize all documents
        tokenized = [_tokenize(doc) for doc in self._documents]
        self._index = BM25Okapi(tokenized)
        logger.info("BM25 index built with %d documents", len(self._ids))

    def search(
        self, query: str, top_k: int = 10, source_filter: str | None = None
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
            if source_filter and self._metadatas[i].get("source") != source_filter:
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
