import logging

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for fast, accurate relevance scoring.

    Replaces LLM-based relevance filtering with a specialized model:
    ~100ms vs 2-3 seconds, with better ranking precision.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        logger.info("Loading reranker model: %s", model_name)
        self.model = CrossEncoder(model_name)
        logger.info("Reranker model loaded")

    def rerank(
        self, query: str, results: list[dict], top_n: int | None = None
    ) -> list[dict]:
        """Rerank retrieval results by cross-encoder relevance score.

        Args:
            query: The user query.
            results: List of retrieval results with "text" field.
            top_n: If set, keep only the top N results after reranking.

        Returns:
            Reranked list of results (most relevant first).
        """
        if not results:
            return results

        pairs = [(query, r["text"]) for r in results]
        scores = self.model.predict(pairs)

        scored = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)

        if top_n:
            scored = scored[:top_n]

        reranked = [r for r, _s in scored]

        if top_n and len(results) > top_n:
            removed = len(results) - len(reranked)
            logger.info("Reranker: %d → %d results (removed %d)", len(results), len(reranked), removed)

        return reranked
