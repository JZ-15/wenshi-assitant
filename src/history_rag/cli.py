import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer(help="二十四史 RAG 写稿助手")
console = Console()


@app.command()
def ingest(
    source: str = typer.Option(None, "--source", "-s", help="只导入指定史书，如: 史记"),
):
    """下载、解析、索引二十四史数据"""
    from history_rag.config import settings
    from history_rag.ingest.downloader import download_data
    from history_rag.ingest.parser import parse_all
    from history_rag.ingest.chunker import chunk_documents
    from history_rag.embeddings.embedder import Embedder
    from history_rag.store.vectordb import VectorStore

    # Download
    json_dir = download_data(settings.data_raw_dir)

    # Parse
    documents = parse_all(json_dir)

    # Filter by source if specified
    if source:
        documents = [d for d in documents if d.source == source]
        if not documents:
            console.print(f"[red]未找到史书「{source}」[/red]")
            raise typer.Exit(1)
        console.print(f"[cyan]只导入「{source}」: {len(documents)} 条记录[/cyan]")

    # Chunk
    console.print("[cyan]分块处理中...[/cyan]")
    chunks = chunk_documents(
        documents,
        max_chars=settings.chunk_max_chars,
        overlap_sentences=settings.chunk_overlap_sentences,
    )
    console.print(f"[green]分块完成: {len(documents)} → {len(chunks)} 块[/green]")

    # Embed and index
    embedder = Embedder(settings.embedding_model, settings.embedding_provider, settings.dashscope_api_key)
    store = VectorStore(settings.chroma_persist_dir, embedder)

    store.add_documents(chunks)
    console.print("[bold green]索引完成！可以开始提问了。[/bold green]")


@app.command()
def ask(
    query: str = typer.Argument(help="你的问题"),
    style: str = typer.Option("default", help="文风: default/academic/blog/storytelling"),
    source: str = typer.Option(None, help="限定史书，如: 史记"),
    top_k: int = typer.Option(None, help="检索数量"),
):
    """向二十四史提问"""
    from history_rag.config import settings
    from history_rag.embeddings.embedder import Embedder
    from history_rag.store.vectordb import VectorStore
    from history_rag.retrieval.retriever import Retriever
    from history_rag.generation.llm import LLM
    from history_rag.generation.prompts import get_system_prompt, format_user_prompt

    if top_k is None:
        top_k = settings.retrieval_top_k

    if not settings.anthropic_api_key:
        console.print("[red]请在 .env 文件中设置 ANTHROPIC_API_KEY[/red]")
        raise typer.Exit(1)

    # Initialize components
    embedder = Embedder(settings.embedding_model, settings.embedding_provider, settings.dashscope_api_key)
    store = VectorStore(settings.chroma_persist_dir, embedder)

    if store.count == 0:
        console.print("[red]数据库为空，请先运行: python -m history_rag ingest[/red]")
        raise typer.Exit(1)

    retriever = Retriever(store)
    llm = LLM(settings.anthropic_api_key, settings.llm_model)

    # Retrieve
    console.print(f"[cyan]检索中 (top_k={top_k})...[/cyan]")
    results, context = retriever.retrieve(query, top_k=top_k, source_filter=source)

    if not results:
        console.print("[yellow]未找到相关内容[/yellow]")
        raise typer.Exit(0)

    # Show sources
    console.print(f"\n[dim]找到 {len(results)} 条相关记录：[/dim]")
    for r in results:
        console.print(f"  [dim]- {r['metadata']['citation']}（{r['metadata']['chapter']}）[/dim]")

    # Generate
    console.print(f"\n[cyan]生成回答 (style={style})...[/cyan]\n")
    system_prompt = get_system_prompt(style)
    user_prompt = format_user_prompt(context, query)
    answer = llm.generate(system_prompt, user_prompt)

    # Display
    console.print(Panel(Markdown(answer), title="回答", border_style="green"))


@app.command()
def serve(
    port: int = typer.Option(8000, help="API 端口号"),
):
    """启动 API 服务"""
    import uvicorn
    console.print(f"[cyan]启动 API 服务: http://localhost:{port}[/cyan]")
    console.print("[cyan]前端请在 frontend/ 目录运行 npm run dev[/cyan]")
    uvicorn.run("history_rag.api:app", host="0.0.0.0", port=port, reload=True)


@app.command()
def stats():
    """显示数据库统计信息"""
    from history_rag.config import settings
    from history_rag.embeddings.embedder import Embedder
    from history_rag.store.vectordb import VectorStore

    embedder = Embedder(settings.embedding_model, settings.embedding_provider, settings.dashscope_api_key)
    store = VectorStore(settings.chroma_persist_dir, embedder)
    console.print(f"向量数据库记录数: [bold]{store.count}[/bold]")


if __name__ == "__main__":
    app()
