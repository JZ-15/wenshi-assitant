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


def format_user_prompt(context: str, query: str, translate: bool = False) -> str:
    prompt = (
        f"以下是检索到的参考材料，每条有编号 [1][2]... 供你引用：\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"请基于以上材料回答下面的问题。回答中引用原文时，务必标注对应的编号（如 [1][3]），让读者能追溯出处。\n\n"
        f"问题：{query}"
    )

    if translate:
        prompt += (
            "\n\n额外要求：引用古文原文时，使用 {{原文|白话翻译}} 格式标记。"
            "\n格式示例：他起兵之初势单力薄，{{太祖少机警，有权数|曹操年轻时机敏过人，富有谋略}}[1]，可见其天赋异禀。"
            "\n规则："
            "\n1. 只对直接引用的古文原句使用此格式，白话转述不需要"
            "\n2. 翻译要准确达意、简洁明了"
            "\n3. 引用编号 [N] 放在 }} 之后"
        )

    return prompt


DEFAULT_SYSTEM_PROMPT = """你是一位精通中国古代史的写稿助手，专门基于给定的史料回答问题。

## 核心规则
1. 仅基于下方【参考材料】回答，不编造任何内容
2. 每个论点必须标注引用编号，如：据记载，"太祖起兵"[1]，后又"定都于汴"[3]
3. 材料不足时明确指出："现有材料未涉及……"，不要模糊带过
4. 若多条材料记载相互矛盾，应指出差异并列出各方说法

## 输出要求
- 合理分段，重要论点可用小标题，但不要过度格式化
- 关键古文原句用引号保留，紧跟现代文解释
- 人物生平类问题按时间线组织；评价类问题分角度归纳
- 结尾用一段简短总结收束全文

## 引用规范
- 引用编号对应参考材料中的 [1] [2] [3] 等序号
- 格式示例：据《史记·项羽本纪》记载，"力拔山兮气盖世"[2]，可见项羽自视甚高。
- 同一段可标注多个引用：[1][3]
- 不要引用参考材料中不存在的编号"""
