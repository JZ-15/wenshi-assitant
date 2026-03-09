import json
import logging

from history_rag.generation.llm import LLM

logger = logging.getLogger(__name__)

HIGHLIGHT_SYSTEM = "你是一个精确的文本标注工具。只返回 JSON，不要任何其他内容。"

HIGHLIGHT_PROMPT = """以下是一篇基于史料写成的回答：
---
{answer}
---

以下是回答所引用的参考材料（编号与回答中的 [1][2]... 对应）：
{sources_block}
---

请分析回答中每个引用编号 [N] 实际引用或转述了对应材料中的哪些句子。

要求：
1. 返回的句子必须是原材料中的原文，一字不差地复制
2. 每条材料最多标注 2 个最关键的句子
3. 如果某条材料在回答中未被实际引用，则对应值为空数组
4. 只返回 JSON 对象

格式示例：
{{"1": ["原文句子a", "原文句子b"], "2": ["原文句子c"], "3": []}}"""


def compute_highlights(
    llm: LLM, answer: str, results: list[dict]
) -> list[list[str]]:
    """Call LLM once to identify highlighted sentences for all sources."""
    if not results:
        return []

    # Build sources block
    parts = []
    for i, r in enumerate(results, 1):
        citation = r["metadata"]["citation"]
        chapter = r["metadata"]["chapter"]
        text = r["text"]
        parts.append(f"[{i}] {citation}（{chapter}）:\n{text}")
    sources_block = "\n\n".join(parts)

    prompt = HIGHLIGHT_PROMPT.format(answer=answer, sources_block=sources_block)

    try:
        raw = llm.generate(HIGHLIGHT_SYSTEM, prompt, max_tokens=1024)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)
        if not isinstance(data, dict):
            logger.warning("Highlight LLM returned non-dict: %s", type(data))
            return [[] for _ in results]

        highlights: list[list[str]] = []
        for i in range(1, len(results) + 1):
            items = data.get(str(i), [])
            if isinstance(items, list):
                highlights.append([s for s in items if isinstance(s, str)][:2])
            else:
                highlights.append([])
        return highlights

    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to compute highlights: %s", e)
        return [[] for _ in results]
