import chromadb
from rich.console import Console
from rich.progress import Progress

from history_rag.ingest.parser import Document
from history_rag.embeddings.embedder import Embedder

console = Console()

BATCH_SIZE = 500  # ChromaDB batch limit


class VectorStore:
    def __init__(self, persist_dir: str, embedder: Embedder):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="twenty_four_histories",
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = embedder

    @property
    def count(self) -> int:
        return self.collection.count()

    def add_documents(self, docs: list[Document]) -> None:
        if not docs:
            return

        # 断点续传：分批查出已入库的 chunk_id，跳过它们
        existing_ids: set[str] = set()
        total = self.count
        if total > 0:
            fetch_batch = 5000
            for offset in range(0, total, fetch_batch):
                batch = self.collection.get(limit=fetch_batch, offset=offset)
                existing_ids.update(batch["ids"])
        remaining = [d for d in docs if d.chunk_id not in existing_ids]

        if not remaining:
            console.print(f"[green]全部 {len(docs)} 个文档块已入库，无需重复处理[/green]")
            return

        if existing_ids:
            console.print(f"[yellow]已入库 {len(existing_ids)} 块，继续处理剩余 {len(remaining)} 块...[/yellow]")
        else:
            console.print(f"[cyan]正在嵌入并写入 {len(remaining)} 个文档块...[/cyan]")

        embed_bs = self.embedder.batch_size
        with Progress() as progress:
            task = progress.add_task("嵌入+索引中...", total=len(remaining))
            for i in range(0, len(remaining), BATCH_SIZE):
                batch_docs = remaining[i : i + BATCH_SIZE]
                texts = [d.text for d in batch_docs]

                # 分小批嵌入（受 API 限制）
                embeddings = []
                for j in range(0, len(texts), embed_bs):
                    sub = texts[j : j + embed_bs]
                    embeddings.extend(self.embedder._call_dashscope(sub) if self.embedder.provider == "dashscope" else self.embedder.embed(sub))

                self.collection.upsert(
                    ids=[d.chunk_id for d in batch_docs],
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[
                        {
                            "source": d.source,
                            "chapter": d.chapter,
                            "section": d.section,
                            "citation": d.citation,
                        }
                        for d in batch_docs
                    ],
                )
                progress.update(task, advance=len(batch_docs))

        console.print(f"[green]索引完成，共 {self.count} 条记录[/green]")

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        source_filter: list[str] | None = None,
    ) -> list[dict]:
        query_embedding = self.embedder.embed_query(query_text)

        if source_filter and len(source_filter) == 1:
            where = {"source": source_filter[0]}
        elif source_filter:
            where = {"source": {"$in": source_filter}}
        else:
            where = None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        for i in range(len(results["ids"][0])):
            retrieved.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })

        return retrieved
