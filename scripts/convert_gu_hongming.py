"""Convert 辜鸿铭资料 TXT files into RAG-ready JSON format.

Reads all .txt files from 辜鸿馓资料/ subdirectories, parses metadata
from the header block, cleans web artifacts, and splits content into
paragraph-level records suitable for chunking by the existing ingest pipeline.

Output: data/raw/ChineseHistoricalSource/json/辜鸿铭资料.json
Each record: {"source": "辜鸿铭资料", "chapter": "<title>·<section>", "text": "...", "chapter_url": "...", "translation": ""}
"""

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "辜鸿馓资料"
OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "ChineseHistoricalSource"
    / "json"
    / "辜鸿铭资料.json"
)

# Category labels derived from folder names
CATEGORY_MAP = {
    "一手著作_中文": "一手著作",
    "百科传记": "百科传记",
    "研究文章_中文": "研究文章",
}

# Lines starting with any of these patterns are web/site junk to strip
JUNK_PATTERNS = [
    re.compile(r"^选择字号："),
    re.compile(r"^(大|中|小)$"),
    re.compile(r"^本文共阅读"),
    re.compile(r"^更新时间："),
    re.compile(r"^进入专题："),
    re.compile(r"^●$"),
    re.compile(r"^本文责编："),
    re.compile(r"^发信站："),
    re.compile(r"^栏目："),
    re.compile(r"^本文链接："),
    re.compile(r"^\d+\s*$"),  # bare numbers (like "10" or "2" at end = recommend count)
    re.compile(r"^推荐$"),
    re.compile(r"^>$"),
    # ctext.org junk
    re.compile(r"^中国哲学书电子化计划"),
    re.compile(r"^维基$"),
    re.compile(r"^简体字版$"),
    re.compile(r"^->"),
    re.compile(r"^\["),  # [查看正文] etc.
    re.compile(r"^URN"),
    re.compile(r"^喜欢"),
    re.compile(r"^我们的网站"),
    re.compile(r"^请支持"),
    re.compile(r"^网站的设计与内容"),
    re.compile(r"^如果您想引用"),
    re.compile(r"^http://ctext"),
    re.compile(r"^请注意"),
    re.compile(r"^严禁使用"),
    re.compile(r"^沪ICP"),
    re.compile(r"^若有任何"),
    re.compile(r"^Do not click"),
]


def _is_junk(line: str) -> bool:
    """Check if a line is web/site junk that should be removed."""
    stripped = line.strip()
    if not stripped:
        return False  # blank lines handled separately
    for pat in JUNK_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def _parse_header(text: str) -> tuple[dict, str]:
    """Split a TXT file into metadata dict and body text."""
    separator = "=" * 20  # at least 20 '=' chars
    parts = text.split("=" * 60, 1)
    if len(parts) < 2:
        # Try a shorter separator
        for n in range(40, 10, -5):
            sep = "=" * n
            if sep in text:
                parts = text.split(sep, 1)
                break

    if len(parts) < 2:
        return {}, text

    header_text, body = parts[0], parts[1]

    meta = {}
    for line in header_text.strip().splitlines():
        line = line.strip()
        if line.startswith("标题："):
            meta["title"] = line[len("标题："):].strip().strip("《》")
        elif line.startswith("作者："):
            meta["author"] = line[len("作者："):].strip()
        elif line.startswith("来源："):
            meta["url"] = line[len("来源："):].strip()

    return meta, body


def _clean_body(body: str) -> str:
    """Remove web junk lines from body text."""
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        if not _is_junk(line):
            cleaned.append(line)
    return "\n".join(cleaned)


def _split_sections_zhangwen(body: str) -> list[tuple[str, str]]:
    """Split 张文襄幕府纪闻 by its ○ section markers.

    Returns list of (section_title, section_text) tuples.
    """
    sections = []
    current_title = ""
    current_lines = []

    for line in body.splitlines():
        stripped = line.strip()
        # Detect section headers like "○南京衙门" or "○不排满" or "●卷下"
        if re.match(r"^[○●]", stripped):
            # Save previous section
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    sections.append((current_title, text))
            current_title = stripped.lstrip("○●").strip()
            current_lines = []
        # Also detect numbered lines that are just section markers (from ctext)
        elif re.match(r"^\d+$", stripped):
            continue  # skip bare line numbers from ctext
        else:
            current_lines.append(line)

    # Last section
    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append((current_title, text))

    return sections


def _split_paragraphs(body: str, min_chars: int = 50, max_chars: int = 800) -> list[str]:
    """Split body into paragraphs suitable for RAG chunking.

    Strategy:
    1. First try splitting on double newlines (blank lines).
    2. If any resulting chunk is still too long, split on single newlines.
    3. Merge very short paragraphs together.
    4. Split any remaining oversized chunks on sentence boundaries.
    """
    # Step 1: split on blank lines
    raw_paras = re.split(r"\n\s*\n", body)
    paras = [p.strip() for p in raw_paras if p.strip()]

    # Step 2: if only 1 big blob, split on single newlines instead
    if len(paras) <= 1 and paras and len(paras[0]) > max_chars:
        paras = [line.strip() for line in body.splitlines() if line.strip()]

    # Step 3: further split any oversized paragraphs on sentence boundaries
    split_paras = []
    for p in paras:
        if len(p) <= max_chars:
            split_paras.append(p)
        else:
            # Split on Chinese sentence-ending punctuation
            sentences = re.split(r'(?<=[。！？；\n])', p)
            buf = ""
            for sent in sentences:
                if buf and len(buf) + len(sent) > max_chars:
                    split_paras.append(buf.strip())
                    buf = sent
                else:
                    buf += sent
            if buf.strip():
                split_paras.append(buf.strip())

    # Step 4: merge very short paragraphs
    merged = []
    buf = ""
    for p in split_paras:
        if buf:
            candidate = buf + "\n" + p
            if len(candidate) <= max_chars:
                buf = candidate
            else:
                merged.append(buf)
                buf = p if len(p) < min_chars else ""
                if len(p) >= min_chars:
                    merged.append(p)
        elif len(p) < min_chars:
            buf = p
        else:
            merged.append(p)
    if buf:
        if merged:
            merged[-1] = merged[-1] + "\n" + buf
        else:
            merged.append(buf)

    return merged


def _is_zhangwen(filepath: Path) -> bool:
    return "张文襄" in filepath.name


def convert_file(filepath: Path, category: str) -> list[dict]:
    """Convert a single TXT file into a list of JSON records."""
    text = filepath.read_text(encoding="utf-8")
    meta, body = _parse_header(text)

    title = meta.get("title", filepath.stem)
    author = meta.get("author", "")
    url = meta.get("url", "")

    body = _clean_body(body)

    records = []

    if _is_zhangwen(filepath):
        # Special handling: split by ○ section markers
        sections = _split_sections_zhangwen(body)
        for section_title, section_text in sections:
            # Further split long sections into paragraphs
            paras = _split_paragraphs(section_text)
            for para in paras:
                para = para.strip()
                if not para or len(para) < 10:
                    continue
                chapter = f"{title}·{section_title}" if section_title else title
                records.append({
                    "source": "辜鸿铭资料",
                    "chapter": f"[{category}] {chapter}（{author}）",
                    "text": para,
                    "chapter_url": url,
                    "translation": "",
                })
    else:
        # General: split into paragraphs
        paras = _split_paragraphs(body)
        for para in paras:
            para = para.strip()
            if not para or len(para) < 10:
                continue
            records.append({
                "source": "辜鸿铭资料",
                "chapter": f"[{category}] {title}（{author}）",
                "text": para,
                "chapter_url": url,
                "translation": "",
            })

    return records


def convert():
    all_records = []

    for subdir in sorted(RAW_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        category = CATEGORY_MAP.get(subdir.name, subdir.name)

        for filepath in sorted(subdir.glob("*.txt")):
            records = convert_file(filepath, category)
            print(f"  {category}/{filepath.name}: {len(records)} records")
            all_records.extend(records)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_records)} records → {OUTPUT}")


if __name__ == "__main__":
    convert()
