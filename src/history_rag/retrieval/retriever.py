from __future__ import annotations

from history_rag.store.vectordb import VectorStore


class Retriever:
    def __init__(self, store: VectorStore, bm25_index=None):
        self.store = store
        self.bm25_index = bm25_index

    def retrieve(
        self,
        query: str | list[str],
        top_k: int = 10,
        source_filter: list[str] | None = None,
    ) -> tuple[list[dict], str]:
        """Retrieve relevant documents and format as context string.

        Args:
            query: Single query string or list of rewritten queries.
            top_k: Number of results per query.
            source_filter: Optional list of source books to filter by.

        Returns:
            (raw_results, formatted_context)
        """
        queries = query if isinstance(query, list) else [query]

        # Retrieve for each query and merge
        all_results = []
        for q in queries:
            results = self.store.query(q, top_k=top_k, source_filter=source_filter)
            all_results.extend(results)

            # BM25 hybrid search
            if self.bm25_index is not None:
                bm25_results = self.bm25_index.search(
                    q, top_k=top_k, source_filter=source_filter
                )
                all_results.extend(bm25_results)

        # Deduplicate by chunk_id first, then by chapter+text
        seen = {}
        for r in all_results:
            # Prefer chunk_id for dedup, fall back to chapter+text
            chunk_key = r.get("id")
            text_key = (r["metadata"]["chapter"], r["text"][:100])
            key = chunk_key or text_key

            if key not in seen or r["distance"] < seen[key]["distance"]:
                seen[key] = r

        deduped = sorted(seen.values(), key=lambda r: r["distance"])

        # Format context with citations
        context_parts = []
        for i, r in enumerate(deduped, 1):
            citation = r["metadata"]["citation"]
            chapter = r["metadata"]["chapter"]
            text = r["text"]
            context_parts.append(f"[{i}] {citation}（{chapter}）:\n{text}")

        context = "\n\n".join(context_parts)
        return deduped, context
