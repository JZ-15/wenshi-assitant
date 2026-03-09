import json
import logging

from history_rag.generation.llm import LLM

logger = logging.getLogger(__name__)

REWRITE_SYSTEM = "你是一个查询改写工具。只返回改写后的独立问题，不要任何其他内容。"

REWRITE_PROMPT = """给定以下对话历史和用户的追问，请将追问改写为一个独立完整的问题（不依赖上下文即可理解）。

对话历史：
{history_block}

用户追问：{query}

规则：
1. 将代词（他、她、它、此人等）替换为具体的人名/事物
2. 补全省略的背景信息
3. 如果追问本身已经是独立完整的问题，则原样返回
4. 只返回改写后的问题文本，不要加引号或其他格式"""


def rewrite_with_context(
    llm: LLM, history: list[dict], query: str
) -> str:
    """Rewrite a follow-up query into a standalone question using conversation history.

    Args:
        llm: LLM instance for rewriting.
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        query: The current user query.

    Returns:
        A standalone query string.
    """
    if not history:
        return query

    # Build history block (keep it concise — last 3 turns max)
    recent = history[-6:]  # 3 rounds = 6 messages
    lines = []
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        # Truncate long assistant responses
        content = msg["content"]
        if msg["role"] == "assistant" and len(content) > 300:
            content = content[:300] + "..."
        lines.append(f"{role}：{content}")
    history_block = "\n".join(lines)

    prompt = REWRITE_PROMPT.format(history_block=history_block, query=query)

    try:
        rewritten = llm.generate(REWRITE_SYSTEM, prompt, max_tokens=256)
        rewritten = rewritten.strip().strip('"').strip("'")
        if rewritten:
            return rewritten
    except Exception as e:
        logger.warning("Context rewrite failed: %s", e)

    return query
