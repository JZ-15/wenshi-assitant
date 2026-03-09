import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from history_rag.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized components
_components = {}


def _init():
    if _components:
        return
    from history_rag.embeddings.embedder import Embedder
    from history_rag.store.vectordb import VectorStore
    from history_rag.retrieval.retriever import Retriever
    from history_rag.generation.llm import LLM

    embedder = Embedder(settings.embedding_model, settings.embedding_provider, settings.dashscope_api_key)
    store = VectorStore(settings.chroma_persist_dir, embedder)
    _components["llm"] = LLM(settings.anthropic_api_key, settings.llm_model)
    _components["store"] = store

    # Build BM25 index for hybrid search
    bm25_index = None
    try:
        from history_rag.retrieval.bm25_index import BM25Index
        bm25_index = BM25Index(store.collection)
    except Exception as e:
        logger.warning("BM25 index initialization failed (falling back to vector-only): %s", e)

    _components["retriever"] = Retriever(store, bm25_index=bm25_index)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init()
    yield


app = FastAPI(title="文史写稿助手 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class AskRequest(BaseModel):
    query: str
    style: str = "default"
    source: str | None = None
    top_k: int = 10
    history: list[dict] = []
    translate: bool = False


class SourceInfo(BaseModel):
    citation: str
    chapter: str
    text: str
    distance: float
    highlights: list[str] = []


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]


class StatsResponse(BaseModel):
    total_records: int
    available_sources: list[str]


AVAILABLE_STYLES = [
    {"id": "default", "name": "默认", "description": "清晰准确，有条理"},
    {"id": "academic", "name": "学术", "description": "严谨考据，大量引用"},
    {"id": "blog", "name": "博客", "description": "通俗生动，适合自媒体"},
    {"id": "storytelling", "name": "叙事", "description": "故事性强，有画面感"},
]

ALL_SOURCES = [
    "史记", "汉书", "后汉书", "三国志", "晋书", "宋书", "南齐书", "梁书",
    "陈书", "魏书", "北齐书", "周书", "隋书", "南史", "北史", "旧唐书",
    "新唐书", "旧五代史", "新五代史", "宋史", "辽史", "金史", "元史", "明史",
]


def _resolve_query(llm, query: str, history: list[dict]) -> str:
    """Apply context rewriting if history is present."""
    if history:
        from history_rag.generation.context_rewriter import rewrite_with_context
        return rewrite_with_context(llm, history, query)
    return query


def _retrieve_and_filter(llm, retriever, query: str, original_query: str, req: AskRequest):
    """Run query rewriting → retrieval → relevance filtering. Returns (results, context)."""
    from history_rag.generation.query_rewriter import rewrite_query
    from history_rag.generation.relevance_filter import filter_relevant

    queries = rewrite_query(llm, query)
    source_filter = req.source if req.source and req.source != "全部" else None
    results, _ = retriever.retrieve(queries, top_k=req.top_k, source_filter=source_filter)

    if not results:
        return [], ""

    results = filter_relevant(llm, original_query, results)

    context_parts = []
    for i, r in enumerate(results, 1):
        citation = r["metadata"]["citation"]
        chapter = r["metadata"]["chapter"]
        text = r["text"]
        context_parts.append(f"[{i}] {citation}（{chapter}）:\n{text}")
    context = "\n\n".join(context_parts)

    return results, context


def _build_sources(results: list[dict], all_highlights: list[list[str]] | None = None) -> list[SourceInfo]:
    """Build SourceInfo list from results with optional highlights."""
    return [
        SourceInfo(
            citation=r["metadata"]["citation"],
            chapter=r["metadata"]["chapter"],
            text=r["text"],
            distance=r["distance"],
            highlights=(all_highlights[i] if all_highlights and i < len(all_highlights) else []),
        )
        for i, r in enumerate(results)
    ]


# --- Routes ---

@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    from history_rag.generation.prompts import get_system_prompt, format_user_prompt
    from history_rag.generation.highlight import compute_highlights

    retriever = _components["retriever"]
    llm = _components["llm"]

    # Context rewriting for multi-turn
    resolved_query = _resolve_query(llm, req.query, req.history)

    # Retrieval + filtering
    results, context = _retrieve_and_filter(llm, retriever, resolved_query, req.query, req)
    if not results:
        return AskResponse(answer="未找到相关内容，请尝试换个问法。", sources=[])

    # Generate answer
    system_prompt = get_system_prompt(req.style)
    user_prompt = format_user_prompt(context, req.query, translate=req.translate)
    answer = llm.generate(system_prompt, user_prompt)

    # Compute highlights
    all_highlights = compute_highlights(llm, answer, results)

    return AskResponse(answer=answer, sources=_build_sources(results, all_highlights))


@app.post("/api/ask/stream")
def ask_stream(req: AskRequest):
    """SSE streaming endpoint.

    Events:
      - event: sources  → JSON array of SourceInfo (without highlights)
      - event: token    → single text token
      - event: highlights → JSON array of highlights per source
      - event: done     → empty
    """
    from history_rag.generation.prompts import get_system_prompt, format_user_prompt
    from history_rag.generation.highlight import compute_highlights

    retriever = _components["retriever"]
    llm = _components["llm"]

    def generate_events():
        # Context rewriting for multi-turn
        resolved_query = _resolve_query(llm, req.query, req.history)

        # Retrieval + filtering
        results, context = _retrieve_and_filter(llm, retriever, resolved_query, req.query, req)

        if not results:
            sources_json = json.dumps([], ensure_ascii=False)
            yield f"event: sources\ndata: {sources_json}\n\n"
            yield f"event: token\ndata: {json.dumps('未找到相关内容，请尝试换个问法。', ensure_ascii=False)}\n\n"
            yield "event: done\ndata: \n\n"
            return

        # Push sources (without highlights yet)
        sources_data = [s.model_dump() for s in _build_sources(results)]
        yield f"event: sources\ndata: {json.dumps(sources_data, ensure_ascii=False)}\n\n"

        # Stream answer tokens
        system_prompt = get_system_prompt(req.style)
        user_prompt = format_user_prompt(context, req.query, translate=req.translate)

        full_answer = []
        for token in llm.stream(system_prompt, user_prompt):
            full_answer.append(token)
            yield f"event: token\ndata: {json.dumps(token, ensure_ascii=False)}\n\n"

        # Compute highlights after answer is complete
        answer_text = "".join(full_answer)
        try:
            all_highlights = compute_highlights(llm, answer_text, results)
            highlights_data = [
                hl if i < len(all_highlights) else []
                for i, hl in enumerate(all_highlights)
            ]
        except Exception as e:
            logger.warning("Highlight computation failed: %s", e)
            highlights_data = [[] for _ in results]

        yield f"event: highlights\ndata: {json.dumps(highlights_data, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: \n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/styles")
def get_styles():
    return AVAILABLE_STYLES


@app.get("/api/sources")
def get_sources():
    return ALL_SOURCES


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    store = _components.get("store")
    total = store.count if store else 0
    return StatsResponse(total_records=total, available_sources=ALL_SOURCES)
