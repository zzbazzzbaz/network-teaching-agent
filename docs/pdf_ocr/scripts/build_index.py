#!/usr/bin/env python3
"""Generate the textbook TOC, agent index and machine-readable page index."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    BOOK_AUTHOR,
    BOOK_TITLE,
    GENERATED_DIR,
    WORK_DIR,
    ensure_dirs,
    fail,
    format_pages,
    read_json,
    write_json,
)


def book_page_label(node: dict[str, Any]) -> str:
    page = node.get("start_book_page")
    return f"（教材 {page}）" if page else ""


def render_toc(nodes: list[dict[str, Any]], depth: int = 0) -> list[str]:
    lines: list[str] = []
    indent = "  " * depth
    for node in nodes:
        if node.get("kind") not in {
            "chapter",
            "appendix",
            "section",
            "subsection",
            "summary",
            "exercises",
        }:
            continue
        title = node.get("raw_title") or node.get("title") or ""
        lines.append(f"{indent}- {title}{book_page_label(node)}")
        children = node.get("children") or []
        if children:
            lines.extend(render_toc(children, depth + 1))
    return lines


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=GENERATED_DIR / "computer-networks")
    args = parser.parse_args()
    ensure_dirs()
    outline = read_json(WORK_DIR / "outline" / "outline.json")
    units_data = read_json(WORK_DIR / "units.json")
    if not outline or not units_data:
        fail("outline.json or units.json missing; run build_sections.py first")
    units: list[dict[str, Any]] = units_data["units"]
    textbook = args.skill_root / "textbook"
    textbook.mkdir(parents=True, exist_ok=True)

    toc_lines = ["# 目录", ""]
    toc_lines.extend(render_toc(outline["nodes"]))
    (textbook / "00-toc.md").write_text("\n".join(toc_lines) + "\n", encoding="utf-8")

    index_lines = [
        f"# {BOOK_TITLE} · {BOOK_AUTHOR}",
        "",
        "| 章节 | 小节 | 标题 | 文件 | 原书页 |",
        "|---|---|---|---|---|",
    ]
    sections = []
    for unit in units:
        chapter = unit.get("chapter")
        chapter_label = str(chapter) if chapter is not None else ""
        section = str(unit.get("section") or "")
        title = str(unit.get("title") or "")
        path = str(unit.get("path") or "")
        pages = format_pages(unit.get("start_book_page"), unit.get("end_book_page"))
        index_lines.append(
            f"| {md_cell(chapter_label)} | {md_cell(section)} | {md_cell(title)} | "
            f"`{md_cell(path)}` | {md_cell(pages)} |"
        )
        sections.append(
            {
                "section": section,
                "title": title,
                "path": path,
                "book_pages": [unit.get("start_book_page"), unit.get("end_book_page")],
            }
        )
    (textbook / "00-index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    pages_payload = {
        "book": {"title": BOOK_TITLE, "author": BOOK_AUTHOR},
        "sections": sections,
    }
    write_json(textbook / "00-pages.json", pages_payload)
    print(f"units: {len(units)}")
    print(f"wrote {textbook / '00-toc.md'}")
    print(f"wrote {textbook / '00-index.md'}")
    print(f"wrote {textbook / '00-pages.json'}")


if __name__ == "__main__":
    main()
