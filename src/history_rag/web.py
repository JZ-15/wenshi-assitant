import gradio as gr

from history_rag.config import settings
from history_rag.embeddings.embedder import Embedder
from history_rag.generation.llm import LLM
from history_rag.generation.prompts import format_user_prompt, get_system_prompt
from history_rag.retrieval.retriever import Retriever
from history_rag.store.vectordb import VectorStore

ALL_SOURCES = [
    "史记", "汉书", "后汉书", "三国志", "晋书", "宋书", "南齐书", "梁书",
    "陈书", "魏书", "北齐书", "周书", "隋书", "南史", "北史", "旧唐书",
    "新唐书", "旧五代史", "新五代史", "宋史", "辽史", "金史", "元史", "明史",
]

STYLES = ["default", "academic", "blog", "storytelling"]

# Lazy-initialized globals
_embedder = None
_store = None
_retriever = None
_llm = None


def _init():
    global _embedder, _store, _retriever, _llm
    if _embedder is None:
        _embedder = Embedder(settings.embedding_model, settings.embedding_provider, settings.dashscope_api_key)
        _store = VectorStore(settings.chroma_persist_dir, _embedder)
        _retriever = Retriever(_store)
        _llm = LLM(settings.anthropic_api_key, settings.llm_model)


def ask(query: str, style: str, source_filter: str, top_k: int) -> str:
    if not query.strip():
        return "请输入问题"

    _init()

    source = source_filter if source_filter != "全部" else None
    results, context = _retriever.retrieve(query, top_k=int(top_k), source_filter=source)

    if not results:
        return "未找到相关内容，请尝试换个问法。"

    system_prompt = get_system_prompt(style)
    user_prompt = format_user_prompt(context, query)
    answer = _llm.generate(system_prompt, user_prompt)

    # Append sources
    sources = "\n\n---\n**参考来源：**\n"
    for r in results:
        sources += f"- {r['metadata']['citation']}（{r['metadata']['chapter']}）\n"

    return answer + sources


def create_app() -> gr.Blocks:
    with gr.Blocks(title="二十四史 AI 写稿助手") as demo:
        gr.Markdown("# 二十四史 AI 写稿助手\n基于 RAG 的文史类写作辅助工具")

        with gr.Row():
            with gr.Column(scale=3):
                query_input = gr.Textbox(
                    label="问题",
                    placeholder="请输入关于二十四史的问题，如：曹操是一个怎样的人？",
                    lines=3,
                )
            with gr.Column(scale=1):
                style_input = gr.Dropdown(STYLES, value="default", label="文风")
                source_input = gr.Dropdown(
                    ["全部"] + ALL_SOURCES, value="全部", label="限定史书"
                )
                top_k_input = gr.Slider(5, 20, value=10, step=1, label="检索数量")

        submit_btn = gr.Button("提问", variant="primary")
        output = gr.Markdown(label="回答")

        submit_btn.click(ask, [query_input, style_input, source_input, top_k_input], output)
        query_input.submit(ask, [query_input, style_input, source_input, top_k_input], output)

    return demo
