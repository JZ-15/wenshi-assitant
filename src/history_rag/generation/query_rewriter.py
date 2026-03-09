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


def rewrite_query(llm: LLM, query: str) -> list[str]:
    """Rewrite user query into 1-3 search queries optimized for classical Chinese retrieval."""
    try:
        result = llm.generate(
            system="你是检索查询改写助手，只返回JSON数组。",
            user=REWRITE_PROMPT.format(query=query),
            max_tokens=256,
        )
        # Parse JSON from response
        text = result.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        queries = json.loads(text)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            console.print(f"[dim]查询改写: {queries}[/dim]")
            return queries
    except (json.JSONDecodeError, Exception) as e:
        console.print(f"[yellow]查询改写失败({e})，使用原始查询[/yellow]")

    return [query]
