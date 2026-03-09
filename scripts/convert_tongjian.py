"""Convert guoxue-study/tongjian JSON data to ChineseHistoricalSource format.

Reads the 294 per-volume JSON files from data/raw/tongjian/resources/_meta/
and produces a single data/raw/ChineseHistoricalSource/json/资治通鉴.json
matching the existing format: [{source, chapter, text, chapter_url, translation}]

Each paragraph becomes one record, same as the 二十四史 data.
The existing chunker handles splitting during ingest.
"""

import json
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
META_DIR = RAW_DIR / "tongjian" / "resources" / "_meta"
OUTPUT = RAW_DIR / "ChineseHistoricalSource" / "json" / "资治通鉴.json"


def convert():
    all_records = []

    for vol_num in range(1, 295):
        filepath = META_DIR / f"{vol_num:03d}.json"
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping")
            continue

        with open(filepath, encoding="utf-8") as f:
            paragraphs = json.load(f)

        chapter_title = f"卷{vol_num}"
        current_section = ""

        for para in paragraphs:
            text = para.get("text", "").strip()
            if not text:
                continue

            # Top-level heading (e.g. "# 周纪 第一章 周纪一")
            if text.startswith("# ") and not text.startswith("## "):
                heading = text.lstrip("# ").strip()
                if chapter_title == f"卷{vol_num}":
                    chapter_title = f"卷{vol_num:03d}·{heading}"
                else:
                    current_section = heading
                continue

            # Year heading (e.g. "## 威烈王二十三年（戊寅，公元前四零三年）")
            if text.startswith("## "):
                current_section = text.lstrip("# ").strip()
                continue

            chapter = chapter_title
            if current_section:
                chapter = f"{chapter_title}·{current_section}"

            all_records.append({
                "source": "资治通鉴",
                "chapter": chapter,
                "text": text,
                "chapter_url": "",
                "translation": "",
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=None)

    print(f"Converted {len(all_records)} records from 294 volumes → {OUTPUT}")


if __name__ == "__main__":
    convert()
