#!/usr/bin/env python3
"""Build section Markdown files from bookmarks and normalized MinerU blocks."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from common import (
    BOOK_AUTHOR,
    BOOK_TITLE,
    GENERATED_DIR,
    WORK_DIR,
    book_page,
    ensure_dirs,
    fail,
    format_pages,
    load_figure_overrides,
    load_pages_by_number,
    normalize_space,
    plan_output_units,
    read_json,
    unit_display_title,
    write_json,
)


def quote_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def html_table_to_markdown(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return ""
    rendered: list[str] = []
    for table in tables:
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = []
            for cell in tr.find_all(["th", "td"]):
                text = normalize_space(cell.get_text(" ", strip=True))
                text = text.replace("|", "\\|")
                cells.append(text)
            if cells:
                rows.append(cells)
        if not rows:
            continue
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        header = rows[0]
        body = rows[1:]
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in body)
        rendered.append("\n".join(lines))
    return "\n\n".join(rendered)


def normalized_anchor(text: str) -> str:
    text = normalize_space(text).lower()
    text = re.sub(r"[\s,，.。;；:：、\-—–_()（）\[\]【】“”\"'‘’]", "", text)
    return text


def is_heading(block: dict[str, Any]) -> bool:
    if block.get("type") == "title":
        return True
    level = block.get("text_level")
    return isinstance(level, int) and level >= 1


def is_boilerplate(text: str) -> bool:
    return normalize_space(text) in {
        "视频讲解",
        "扫一扫",
        "扫码观看",
        "更多资源",
    }


def anchor_candidates(unit: dict[str, Any]) -> list[str]:
    section = str(unit.get("section") or "")
    title = str(unit.get("title") or "")
    kind = unit.get("kind")
    chapter = unit.get("chapter")
    candidates = [f"{section}{title}", title]
    if kind in {"chapter-intro", "chapter"} and chapter is not None:
        candidates.append(f"第{chapter}章{title}")
        candidates.append(f"{chapter}{title}")
    if kind == "appendix":
        candidates.append(f"附录{section}{title}")
    if kind == "sum":
        pass
    return [normalized_anchor(candidate) for candidate in candidates if candidate]


def ordered_blocks(pages: dict[int, list[dict[str, Any]]]) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for pdf_page in sorted(pages):
        for block in pages[pdf_page]:
            rows.append((pdf_page, block))
    return rows


def find_anchor(
    unit: dict[str, Any],
    blocks: list[tuple[int, dict[str, Any]]],
    start: int,
    end: int,
) -> int | None:
    candidates = anchor_candidates(unit)
    if not candidates:
        return None
    fallback: int | None = None
    for index, (pdf_page, block) in enumerate(blocks):
        if pdf_page < start or pdf_page > min(end, start + 2):
            continue
        text = normalize_space(block.get("text") or block.get("caption") or "")
        if not text or len(text) > 180:
            continue
        block_key = normalized_anchor(text)
        if not block_key:
            continue
        if fallback is None:
            fallback = index
        for candidate in candidates:
            if block_key == candidate or block_key.startswith(candidate):
                if is_heading(block) or len(block_key) <= len(candidate) + 12:
                    return index
    return fallback


def prefix_unit(unit: dict[str, Any]) -> dict[str, Any] | None:
    section = unit.get("prefix_section")
    title = unit.get("prefix_title")
    if not section or not title:
        return None
    return {
        "section": section,
        "title": title,
        "kind": unit.get("prefix_kind") or "section",
        "chapter": unit.get("chapter"),
    }


def block_range_for_units(
    units: list[dict[str, Any]],
    pages: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    blocks = ordered_blocks(pages)
    units = [dict(unit) for unit in units]
    anchors: list[int | None] = []
    for unit in units:
        anchors.append(
            find_anchor(
                unit,
                blocks,
                int(unit["start_pdf_page"]),
                int(unit["end_pdf_page"]),
            )
        )

    # If a chapter has no separate intro file, let its first section absorb the
    # chapter heading/introduction. Same for a section that was split into
    # subsections without a section-intro file.
    chapter_first: dict[Any, int] = {}
    for index, unit in enumerate(units):
        chapter = unit.get("chapter")
        if chapter not in chapter_first:
            chapter_first[chapter] = index
    for chapter, index in chapter_first.items():
        first = units[index]
        has_intro = any(
            unit.get("kind") == "chapter-intro" and unit.get("chapter") == chapter for unit in units
        )
        if not has_intro:
            first["prefix_section"] = str(first.get("chapter"))
            first["prefix_title"] = first.get("chapter_title") or ""
            first["prefix_from_pdf_page"] = int(first["start_pdf_page"])
            first["prefix_kind"] = "chapter"

    parent_first: dict[str, int] = {}
    for index, unit in enumerate(units):
        parent = unit.get("parent_section")
        # Only split subsections inherit the parent section heading. Units
        # whose parent is a chapter (e.g. 6.2 -> 6) must start at their own
        # bookmark, otherwise they absorb the whole chapter before them.
        if parent and "." in str(parent) and parent not in parent_first:
            parent_first[parent] = index
    for parent, index in parent_first.items():
        first = units[index]
        has_intro = any(
            unit.get("parent_section") == parent and unit.get("kind") == "section-intro"
            for unit in units
        )
        if not has_intro:
            first["prefix_section"] = parent
            first["prefix_title"] = first.get("parent_title") or ""
            first["prefix_from_pdf_page"] = int(
                first.get("parent_start_pdf_page") or first["start_pdf_page"]
            )
            first["prefix_kind"] = "section"

    effective_anchors: list[int | None] = []
    for index, unit in enumerate(units):
        prefix = prefix_unit(unit)
        if prefix:
            prefix_anchor = find_anchor(
                prefix,
                blocks,
                int(unit.get("prefix_from_pdf_page") or unit["start_pdf_page"]),
                int(unit["end_pdf_page"]),
            )
            if prefix_anchor is not None:
                effective_anchors.append(prefix_anchor)
                continue
        effective_anchors.append(anchors[index])

    last_index = len(blocks) - 1
    for index, unit in enumerate(units):
        start_index = effective_anchors[index]
        if start_index is None:
            start_page = int(unit.get("prefix_from_pdf_page") or unit["start_pdf_page"])
            start_index = next(
                (i for i, (page, _) in enumerate(blocks) if page >= start_page),
                None,
            )
        if start_index is None:
            unit["start_index"] = 0
            unit["end_index"] = -1
            continue

        end_index = None
        next_anchor = effective_anchors[index + 1] if index + 1 < len(units) else None
        if next_anchor is not None and next_anchor > start_index:
            end_index = next_anchor - 1
        if end_index is None:
            end_page = int(unit["end_pdf_page"])
            end_index = max(
                start_index,
                max(
                    (i for i, (page, _) in enumerate(blocks) if page <= end_page),
                    default=last_index,
                ),
            )
        unit["start_index"] = start_index
        unit["end_index"] = min(end_index, last_index)

        selected = blocks[unit["start_index"] : unit["end_index"] + 1]
        if selected:
            unit["start_pdf_page"] = selected[0][0]
            unit["end_pdf_page"] = selected[-1][0]
            unit["start_book_page"] = book_page(unit["start_pdf_page"])
            unit["end_book_page"] = book_page(unit["end_pdf_page"])
    return units


def block_markdown(
    block: dict[str, Any],
    unit: dict[str, Any],
    page_number: int,
    figure_map: dict[str, str],
    figure_overrides: dict[str, dict[str, str]],
) -> str:
    block_type = block.get("type") or "text"
    text = normalize_space(block.get("text") or "")
    caption = normalize_space(block.get("caption") or "")
    override = figure_overrides.get(str(block.get("img_path") or ""), {})
    if override.get("caption"):
        caption = normalize_space(str(override["caption"]))
    book = book_page(page_number)

    if block_type in {"header", "footer", "page_number"}:
        return ""
    if block_type == "table":
        table = html_table_to_markdown(str(block.get("table_body") or ""))
        label = caption or text
        parts = []
        if label:
            parts.append(f"> {label}（教材第 {book} 页）" if book else f"> {label}")
        if table:
            parts.append(table)
        return "\n\n".join(parts)
    if block_type == "image":
        if any(marker in caption for marker in ("扫一扫", "扫码", "二维码", "视频讲解")):
            return ""
        relative = figure_map.get(str(block.get("image_path") or ""))
        if not caption:
            if not relative:
                return ""
            alt = f"教材第 {book} 页图片" if book else "教材图片"
            return f"![{alt}](../../figures/{relative})"
        caption_line = f"> {caption}（教材第 {book} 页）" if book else f"> {caption}"
        if relative:
            alt = caption.replace("[", "\\[").replace("]", "\\]")
            return f"![{alt}](../../figures/{relative})\n\n{caption_line}"
        return caption_line
    if block_type == "page_footnote":
        if not text:
            return ""
        return f"> {text}"
    if block_type == "equation":
        if not text:
            return ""
        return text if "$" in text else f"$$\n{text}\n$$"
    if not text:
        return ""
    if is_heading(block):
        if is_boilerplate(text):
            return ""
        display = unit_display_title(unit)
        if normalized_anchor(text) in {
            normalized_anchor(display),
            normalized_anchor(str(unit.get("title") or "")),
            normalized_anchor(f"{unit.get('section', '')} {unit.get('title', '')}"),
        }:
            return ""
        return f"## {text}"
    if is_boilerplate(text):
        return ""
    paragraphs = [normalize_space(part) for part in text.split("\n\n")]
    paragraphs = [part for part in paragraphs if part]
    return "\n\n".join(paragraphs)


def render_unit(
    unit: dict[str, Any],
    blocks: list[tuple[int, dict[str, Any]]],
    figure_map: dict[str, str],
    figure_overrides: dict[str, dict[str, str]],
) -> str:
    start = int(unit.get("start_index", 0))
    end = int(unit.get("end_index", -1))
    selected = blocks[start : end + 1] if end >= start else []
    body: list[str] = []
    previous = ""
    for page_number, block in selected:
        markdown = block_markdown(block, unit, page_number, figure_map, figure_overrides)
        if not markdown or markdown == previous:
            continue
        body.append(markdown)
        previous = markdown
    if not body:
        pages = format_pages(unit.get("start_book_page"), unit.get("end_book_page"))
        body.append(f"（本小节 OCR 未识别到正文，请对照教材第 {pages} 页。）")
    return "\n\n".join(body).strip() + "\n"


def section_frontmatter(unit: dict[str, Any]) -> str:
    section = quote_yaml(str(unit.get("section") or ""))
    title = quote_yaml(str(unit.get("title") or ""))
    start = unit.get("start_book_page")
    end = unit.get("end_book_page")
    pages = f"[{start}, {end}]" if start is not None and end is not None else "[]"
    return f'---\nsection: "{section}"\ntitle: "{title}"\nbook_pages: {pages}\n---\n'


def write_unit_file(root: Path, unit: dict[str, Any], content: str) -> dict[str, Any]:
    path = root / "textbook" / unit["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    display = unit_display_title(unit)
    path.write_text(
        section_frontmatter(unit) + f"\n# {display}\n\n{content}",
        encoding="utf-8",
    )
    unit = dict(unit)
    unit["file"] = str(path.relative_to(root))
    unit["display_title"] = display
    unit["book_pages_label"] = format_pages(unit.get("start_book_page"), unit.get("end_book_page"))
    return unit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    outline = read_json(WORK_DIR / "outline" / "outline.json")
    if not outline:
        fail("outline.json missing; run extract_outline.py first")
    pages = load_pages_by_number()
    if not pages:
        fail("pages.jsonl missing; run normalize_api_output.py first")

    units = plan_output_units(outline["nodes"], pages)
    if not units:
        fail("no output units generated")
    blocks = ordered_blocks(pages)
    units = block_range_for_units(units, pages)

    figures_payload = read_json(WORK_DIR / "figures.json", {"figures": []})
    figure_overrides = load_figure_overrides()
    figure_map = {
        str(row["source_path"]): str(row["file"])
        for row in figures_payload.get("figures", [])
        if row.get("source_path") and row.get("file")
    }
    root = GENERATED_DIR / "computer-networks"
    textbook_root = root / "textbook"
    if textbook_root.exists() and not args.no_clean:
        shutil.rmtree(textbook_root)
    textbook_root.mkdir(parents=True, exist_ok=True)
    (root / "figures").mkdir(parents=True, exist_ok=True)

    output_units: list[dict[str, Any]] = []
    for unit in units:
        content = render_unit(unit, blocks, figure_map, figure_overrides)
        if not content.strip():
            continue
        # Drop an empty chapter/section intro if it ended up with only the
        # generated placeholder.
        if "(本小节 OCR 未识别到正文" in content and unit.get("kind") in {
            "chapter-intro",
            "section-intro",
        }:
            continue
        written = write_unit_file(root, unit, content)
        output_units.append(written)

    write_json(
        WORK_DIR / "units.json",
        {
            "book": {"title": BOOK_TITLE, "author": BOOK_AUTHOR},
            "units": output_units,
        },
    )
    total = sum((root / "textbook" / unit["path"]).stat().st_size for unit in output_units)
    print(f"units: {len(output_units)}; textbook bytes: {total}")
    print(f"wrote {root / 'textbook'}")


if __name__ == "__main__":
    main()
