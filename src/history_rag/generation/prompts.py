from pathlib import Path

from history_rag.config import settings


def _load_template(name: str) -> str:
    filepath = Path(settings.prompts_dir) / name
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    return ""


def get_system_prompt(style: str = "default") -> str:
    # Try style-specific template first
    template = _load_template(f"style_{style}.txt")
    if not template:
        template = _load_template("system_default.txt")
    if not template:
        template = DEFAULT_SYSTEM_PROMPT
    return template


def format_user_prompt(context: str, query: str) -> str:
    return f"参考材料：\n{context}\n\n问题：{query}"


DEFAULT_SYSTEM_PROMPT = """你是一位精通中国古代史的写稿助手，专门基于二十四史原文回答问题。

规则：
1. 仅基于下方提供的原文材料回答，不要编造内容
2. 引用原文时标注出处，格式如：《史记·项羽本纪》
3. 如果材料不足以回答问题，明确说明哪些方面缺乏材料
4. 用现代中文解释，但保留关键古文原句并加以解释
5. 回答要有条理，使用适当的分段和标题
6. 对于人物生平类问题，按时间线组织；对于评价类问题，分类归纳不同观点"""
