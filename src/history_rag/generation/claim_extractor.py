import json
import logging
import re

from rich.console import Console

from history_rag.generation.llm import LLM

logger = logging.getLogger(__name__)
console = Console()

CLAIM_EXTRACTION_PROMPT = """从以下稿件中提取所有可以用史料验证的史实断言。

规则：
1. 每条断言应独立、具体、可用史料验证（涉及具体人物、事件、时间、地点、因果关系、数字等）
2. 跳过以下内容：
   - 作者的主观评价和个人观点（如"他是最伟大的皇帝"）
   - 过渡句和修辞（如"接下来我们看看"、"众所周知"）
   - 纯粹的文学描写和抒情
   - 不涉及具体史实的泛泛而论
3. 保留断言在原文中的核心表述，保持简洁，必要时补充上下文使其可独立理解
4. 如果一句话包含多个可验证事实，拆分为多条断言

返回 JSON 数组，每个元素是一条断言字符串。
示例：["建安五年曹操在官渡击败袁绍", "赤壁之战后孙刘联盟瓦解"]

稿件内容：
"""


def extract_claims(llm: LLM, article: str) -> list[str]:
    """Extract verifiable historical claims from an article.

    Args:
        llm: LLM instance for claim extraction.
        article: The article text to analyze.

    Returns:
        List of claim strings.
    """
    system = "你是一位史料审核助手，擅长从文章中识别可验证的史实断言。只返回 JSON 数组，不要其他内容。"
    user = CLAIM_EXTRACTION_PROMPT + article

    try:
        response = llm.generate(system, user, max_tokens=4096)
        # Extract JSON array from response
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            claims = json.loads(match.group())
            if isinstance(claims, list) and all(isinstance(c, str) for c in claims):
                logger.info("Extracted %d claims from article", len(claims))
                return claims
    except Exception as e:
        logger.warning("Claim extraction failed: %s", e)

    # Fallback: split by Chinese sentence endings
    logger.warning("Falling back to sentence splitting")
    sentences = re.split(r'[。！？]', article)
    return [s.strip() for s in sentences if len(s.strip()) > 10]
