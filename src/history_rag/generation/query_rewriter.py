import json
from rich.console import Console

from history_rag.generation.llm import LLM

console = Console()

REWRITE_PROMPT = """你是一个中国古代史料检索专家。用户会提出关于二十四史的问题，你需要将其改写为1-3个适合在古文向量数据库中检索的查询。

改写要求：
1. 提取关键的人名、事件、朝代、官职等实体
2. 用简洁的短语而非完整句子，更接近古文表述
3. 从不同角度覆盖问题的各个方面
4. 如果问题涉及对比，为每个对比对象生成独立查询

示例：
问题：项羽为什么会失败？
输出：["项羽败亡垓下乌江", "项羽刘邦楚汉相争", "项羽性格用人"]

问题：唐太宗是如何治理国家的？
输出：["唐太宗贞观之治", "太宗纳谏用人", "唐太宗治国政策"]

问题：对比曹操和刘备的用人之道
输出：["曹操用人唯才", "刘备用人仁义", "曹操刘备人才"]

请只返回JSON数组，不要其他内容。

问题：{query}"""


REWRITE_WITH_CONTEXT_PROMPT = """你是一个中国古代史料检索专家。根据对话历史和用户的追问，生成1-3个适合在古文向量数据库中检索的查询。

对话历史：
{history_block}

用户追问：{query}

改写要求：
1. 先将追问中的代词（他、她、此人等）替换为对话中提到的具体人名/事物
2. 提取关键的人名、事件、朝代、官职等实体
3. 用简洁的短语而非完整句子，更接近古文表述
4. 从不同角度覆盖问题的各个方面

请只返回JSON数组，不要其他内容。"""


def _parse_query_list(result: str, fallback: str) -> list[str]:
    """Parse a JSON array of query strings from LLM output."""
    text = result.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    queries = json.loads(text)
    if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
        console.print(f"[dim]查询改写: {queries}[/dim]")
        return queries
    return [fallback]


def rewrite_query(llm: LLM, query: str) -> list[str]:
    """Rewrite user query into 1-3 search queries optimized for classical Chinese retrieval."""
    try:
        result = llm.generate(
            system="你是检索查询改写助手，只返回JSON数组。",
            user=REWRITE_PROMPT.format(query=query),
            max_tokens=256,
        )
        return _parse_query_list(result, query)
    except (json.JSONDecodeError, Exception) as e:
        console.print(f"[yellow]查询改写失败({e})，使用原始查询[/yellow]")

    return [query]


def rewrite_query_with_context(
    llm: LLM, history: list[dict], query: str
) -> list[str]:
    """Combined context rewriting + query expansion in a single LLM call.

    When history is empty, behaves like rewrite_query().
    When history is present, resolves pronouns AND generates search queries
    in one call (saves one LLM round-trip vs separate context_rewriter + query_rewriter).
    """
    if not history:
        return rewrite_query(llm, query)

    # Build history block (last 3 turns)
    recent = history[-6:]
    lines = []
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 300:
            content = content[:300] + "..."
        lines.append(f"{role}：{content}")
    history_block = "\n".join(lines)

    try:
        result = llm.generate(
            system="你是检索查询改写助手，只返回JSON数组。",
            user=REWRITE_WITH_CONTEXT_PROMPT.format(
                history_block=history_block, query=query
            ),
            max_tokens=256,
        )
        return _parse_query_list(result, query)
    except (json.JSONDecodeError, Exception) as e:
        console.print(f"[yellow]上下文查询改写失败({e})，使用原始查询[/yellow]")

    return [query]
