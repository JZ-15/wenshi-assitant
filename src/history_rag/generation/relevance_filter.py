import json
from rich.console import Console

from history_rag.generation.llm import LLM

console = Console()

FILTER_PROMPT = """你是一个史料相关性判断专家。给定一个用户问题和一组检索到的古文片段，判断每条片段是否与问题相关。

用户问题：{query}

检索结果：
{passages}

请对每条结果判断是否与问题相关，返回一个JSON数组，每项为 true（相关）或 false（不相关）。
只返回JSON数组，如 [true, false, true, ...]，不要其他内容。"""


def filter_relevant(llm: LLM, query: str, results: list[dict]) -> list[dict]:
    """Filter retrieval results by LLM-judged relevance."""
    if not results:
        return results

    # Format passages for LLM
    passages = []
    for i, r in enumerate(results, 1):
        citation = r["metadata"]["citation"]
        text = r["text"][:200]  # Truncate for efficiency
        passages.append(f"[{i}] {citation}: {text}")
    passages_text = "\n".join(passages)

    try:
        result = llm.generate(
            system="你是史料相关性判断助手，只返回JSON数组。",
            user=FILTER_PROMPT.format(query=query, passages=passages_text),
            max_tokens=256,
        )
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        judgments = json.loads(text)

        if isinstance(judgments, list) and len(judgments) == len(results):
            filtered = [r for r, keep in zip(results, judgments) if keep]
            removed = len(results) - len(filtered)
            if removed:
                console.print(f"[dim]相关性过滤: {len(results)} → {len(filtered)} 条（移除 {removed} 条噪声）[/dim]")
            # Keep at least 1 result
            if not filtered:
                filtered = results[:1]
                console.print("[yellow]过滤后无结果，保留最相关的1条[/yellow]")
            return filtered
    except (json.JSONDecodeError, Exception) as e:
        console.print(f"[yellow]相关性过滤失败({e})，使用全部结果[/yellow]")

    return results
