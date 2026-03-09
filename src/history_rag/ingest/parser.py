import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class Document:
    text: str
    source: str  # e.g. "史记"
    chapter: str  # e.g. "卷一·五帝本纪第一"
    section: str = ""  # parsed section name, e.g. "五帝本纪"
    citation: str = ""  # e.g. "《史记·五帝本纪》"
    chunk_id: str = ""
    translation: str = ""


def _extract_section(chapter: str) -> str:
    """Extract section name from chapter string.

    Examples:
        '卷一·五帝本纪第一' -> '五帝本纪'
        '卷七十·张仪列传第十' -> '张仪列传'
    """
    # Remove 卷X· prefix
    parts = chapter.split("·", 1)
    section = parts[1] if len(parts) > 1 else parts[0]
    # Remove trailing 第X or 第XX
    section = re.sub(r"第[一二三四五六七八九十百千\d]+$", "", section).strip()
    return section


def _build_citation(source: str, section: str) -> str:
    if section:
        return f"《{source}·{section}》"
    return f"《{source}》"


def parse_json_file(filepath: Path) -> list[Document]:
    """Parse a single JSON file into Document objects."""
    with open(filepath, "r", encoding="utf-8") as f:
        records = json.load(f)

    documents = []
    for i, record in enumerate(records):
        text = record.get("text", "").strip()
        if not text:
            continue

        source = record.get("source", filepath.stem)
        chapter = record.get("chapter", "")
        translation = record.get("translation", "")

        # Skip if translation is a URL (not actual translation text)
        if isinstance(translation, str) and translation.startswith("http"):
            translation = ""

        section = _extract_section(chapter)
        citation = _build_citation(source, section)
        chunk_id = f"{source}_{i:06d}"

        documents.append(Document(
            text=text,
            source=source,
            chapter=chapter,
            section=section,
            citation=citation,
            chunk_id=chunk_id,
            translation=translation,
        ))

    return documents


def parse_all(json_dir: str | Path) -> list[Document]:
    """Parse all JSON files in the directory."""
    json_path = Path(json_dir)
    all_docs = []

    json_files = sorted(json_path.glob("*.json"))
    console.print(f"[cyan]找到 {len(json_files)} 个史书文件[/cyan]")

    for filepath in json_files:
        docs = parse_json_file(filepath)
        console.print(f"  {filepath.stem}: {len(docs)} 条记录")
        all_docs.extend(docs)

    console.print(f"[green]共解析 {len(all_docs)} 条记录[/green]")
    return all_docs
