from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from history_rag.config import settings

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
    _components["retriever"] = Retriever(store)
    _components["llm"] = LLM(settings.anthropic_api_key, settings.llm_model)
    _components["store"] = store


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


class SourceInfo(BaseModel):
    citation: str
    chapter: str
    text: str
    distance: float


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


# --- Routes ---

@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    from history_rag.generation.prompts import get_system_prompt, format_user_prompt

    retriever = _components["retriever"]
    llm = _components["llm"]

    source_filter = req.source if req.source and req.source != "全部" else None
    results, context = retriever.retrieve(
        req.query, top_k=req.top_k, source_filter=source_filter
    )

    if not results:
        return AskResponse(answer="未找到相关内容，请尝试换个问法。", sources=[])

    system_prompt = get_system_prompt(req.style)
    user_prompt = format_user_prompt(context, req.query)
    answer = llm.generate(system_prompt, user_prompt)

    sources = [
        SourceInfo(
            citation=r["metadata"]["citation"],
            chapter=r["metadata"]["chapter"],
            text=r["text"],
            distance=r["distance"],
        )
        for r in results
    ]

    return AskResponse(answer=answer, sources=sources)


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
