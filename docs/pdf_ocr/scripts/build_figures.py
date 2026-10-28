#!/usr/bin/env python3
"""Copy all captioned textbook figures and build figures/index.md."""

from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import (
    GENERATED_DIR,
    WORK_DIR,
    chapter_dir,
    ensure_dirs,
    fail,
    load_figure_overrides,
    normalize_space,
    read_json,
    read_jsonl,
    write_json,
)

FIGURE_RE = re.compile(r"图\s*(\d+)\s*[-–—]\s*(\d+)")
APPENDIX_FIGURE_RE = re.compile(r"图\s*([A-Z])\s*[-–—]\s*(\d+)")
BOILERPLATE = ("扫一扫", "扫码", "二维码", "视频讲解")


def _plain(text: str) -> str:
    return re.sub(r"[\s，。；：、,.!?！？（）()《》“”\"'‘’\-—–]", "", text).lower()


def caption_info(caption: str) -> tuple[int | str | None, str | None, str]:
    normalized = normalize_space(caption)
    match = FIGURE_RE.search(normalized)
    if match:
        chapter: int | str = int(match.group(1))
        number = str(int(match.group(2)))
        title = normalize_space(normalized[match.end() :])
        return chapter, number, title or normalized
    match = APPENDIX_FIGURE_RE.search(normalized)
    if match:
        chapter = match.group(1).upper()
        number = str(int(match.group(2)))
        title = normalize_space(normalized[match.end() :])
        return chapter, number, title or normalized
    return None, None, normalized


def load_sections() -> list[dict[str, Any]]:
    sections = read_json(WORK_DIR / "outline" / "sections.json", [])
    if not sections:
        fail("work/outline/sections.json missing; run extract_outline.py first")
    return [
        row
        for row in sections
        if row.get("kind")
        in {"chapter", "appendix", "section", "subsection", "summary", "exercises"}
    ]


def find_section(
    sections: list[dict[str, Any]],
    book_page: int | None,
    caption: str = "",
) -> dict[str, Any] | None:
    if book_page is None:
        return None
    candidates = []
    for row in sections:
        start = row.get("start_book_page")
        end = row.get("end_book_page")
        if start is None or end is None:
            continue
        if start <= book_page <= end:
            candidates.append(row)
    if not candidates:
        return None

    caption_key = _plain(caption)
    title_matches = [
        row
        for row in candidates
        if len(_plain(str(row.get("title") or ""))) >= 4
        and _plain(str(row.get("title") or "")) in caption_key
    ]
    if title_matches:
        return sorted(
            title_matches,
            key=lambda row: -len(_plain(str(row.get("title") or ""))),
        )[0]

    def score(row: dict[str, Any]) -> tuple[int, int]:
        kind = row.get("kind")
        kind_score = 0 if kind in {"section", "subsection", "chapter"} else 1
        return kind_score, int(row.get("start_book_page") or 0)

    return sorted(candidates, key=score)[0]


def find_chapter(sections: list[dict[str, Any]], pdf_page: int) -> int | str | None:
    for row in sections:
        if row.get("kind") not in {"chapter", "appendix"}:
            continue
        start = row.get("start_pdf_page")
        end = row.get("end_pdf_page")
        if start is not None and end is not None and int(start) <= pdf_page <= int(end):
            return row.get("chapter")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-bytes", type=int, default=0)
    args = parser.parse_args()
    ensure_dirs()
    sections = load_sections()
    overrides = load_figure_overrides()
    pages = read_jsonl(WORK_DIR / "pages" / "pages.jsonl")
    if not pages:
        fail("pages.jsonl missing; run normalize_api_output.py first")

    root = GENERATED_DIR / "computer-networks"
    figures_root = root / "figures"
    figures_root.mkdir(parents=True, exist_ok=True)
    # Keep the expensive vision-model sidecars when rebuilding image assets.
    for child in list(figures_root.iterdir()):
        if child.name == "descriptions":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    rows: list[dict[str, Any]] = []
    used_targets: dict[Path, Path] = {}
    unnumbered: dict[tuple[int | str | None, int | None], int] = defaultdict(int)
    for page in pages:
        pdf_page = int(page["pdf_page"])
        book = page.get("book_page")
        for block in page.get("blocks", []):
            if block.get("type") != "image":
                continue
            caption = normalize_space(block.get("caption") or "")
            override = overrides.get(str(block.get("img_path") or ""), {})
            if override.get("caption"):
                caption = normalize_space(str(override["caption"]))
            if any(marker in caption for marker in BOILERPLATE):
                continue
            source = Path(str(block.get("image_path") or ""))
            if not source.is_file() or source.stat().st_size < args.min_bytes:
                continue

            # MinerU sometimes separates a figure from its caption, especially
            # for (a)/(b) subfigures. Keep large uncaptioned image blocks so
            # the actual image is not lost; tiny QR/video icons stay excluded.
            if not caption:
                bbox = block.get("bbox") or []
                if len(bbox) != 4:
                    continue
                width = float(bbox[2]) - float(bbox[0])
                height = float(bbox[3]) - float(bbox[1])
                if book is None or width < 200 or width * height < 20_000:
                    continue

            chapter, number, title = caption_info(caption)
            if override.get("title"):
                title = normalize_space(str(override["title"]))
            section = find_section(sections, book, caption)
            if chapter is None:
                chapter = section.get("chapter") if section else find_chapter(sections, pdf_page)
            if chapter is None:
                chapter = "misc"

            if override.get("file_stem"):
                stem = str(override["file_stem"])
            elif number is not None:
                stem = f"fig-{chapter}-{int(number):02d}"
            else:
                key = (chapter, book)
                unnumbered[key] += 1
                stem = f"page-{book or 0}-fig-{unnumbered[key]:02d}"

            suffix = source.suffix.lower() or ".png"
            relative = Path(chapter_dir(chapter)) / f"{stem}{suffix}"
            while relative in used_targets and used_targets[relative] != source:
                relative = Path(chapter_dir(chapter)) / f"{stem}-{len(used_targets) + 1}{suffix}"
            used_targets[relative] = source
            target = figures_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

            label = str(
                override.get("label")
                or (f"图 {chapter}-{number}" if number else f"图（教材第 {book} 页）")
            )
            rows.append(
                {
                    "chapter": chapter,
                    "number": number,
                    "caption": caption,
                    "title": title,
                    "label": label,
                    "book_page": book,
                    "pdf_page": pdf_page,
                    "section": section.get("section") if section else None,
                    "source_path": str(source),
                    "file": str(relative),
                    "size": source.stat().st_size,
                }
            )

    def sort_key(row: dict[str, Any]) -> tuple[str, int, str]:
        chapter = row.get("chapter")
        chapter_key = f"{int(chapter):02d}" if isinstance(chapter, int) else str(chapter)
        number = row.get("number")
        return (
            chapter_key,
            int(number) if str(number or "").isdigit() else 9999,
            str(row.get("caption") or ""),
        )

    rows.sort(key=sort_key)
    index_lines = [
        "# 图表索引",
        "",
        "> 已收录全部教材图片（含子图和无图注大图，排除二维码/视频入口）。",
        "> 图片文件位于 `figures/` 对应章节目录。",
        "",
        "| 图号 | 图题 | 教材页 | 文件 | 关联小节 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        title = (
            row.get("title") or row.get("caption") or f"教材第 {row.get('book_page')} 页图片"
        ).replace("|", "\\|")
        index_lines.append(
            f"| {row['label']} | {title} | {row.get('book_page') or '—'} | "
            f"`{row['file']}` | {row.get('section') or '—'} |"
        )
    if not rows:
        index_lines.append("| — | 未识别到带图注的图片 | — | — | — |")
    (figures_root / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    write_json(WORK_DIR / "figures.json", {"figures": rows})
    print(f"figures: {len(rows)}")
    print(f"wrote {figures_root / 'index.md'}")


if __name__ == "__main__":
    main()
