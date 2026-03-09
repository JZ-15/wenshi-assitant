from history_rag.store.vectordb import VectorStore


class Retriever:
    def __init__(self, store: VectorStore):
        self.store = store

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> tuple[list[dict], str]:
        """Retrieve relevant documents and format as context string.

        Returns:
            (raw_results, formatted_context)
        """
        results = self.store.query(query, top_k=top_k, source_filter=source_filter)

        # Deduplicate by chapter+text (keep higher relevance)
        seen = set()
        deduped = []
        for r in results:
            key = (r["metadata"]["chapter"], r["text"][:100])
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        # Format context with citations
        context_parts = []
        for i, r in enumerate(deduped, 1):
            citation = r["metadata"]["citation"]
            chapter = r["metadata"]["chapter"]
            text = r["text"]
            context_parts.append(f"[{i}] {citation}（{chapter}）:\n{text}")

        context = "\n\n".join(context_parts)
        return deduped, context
