#!/usr/bin/env python3
"""Extract the PDF bookmark tree and turn it into section/page metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    BOOK_PAGE_OFFSET,
    EXPECTED_PAGE_COUNT,
    WORK_DIR,
    book_page,
    ensure_dirs,
    fail,
    normalize_space,
    parse_heading,
    source_pdf_path,
    write_json,
)
from pypdf import PdfReader


def destination_page(reader: PdfReader, item: Any) -> int | None:
    try:
        if isinstance(item, list):
            return destination_page(reader, item[0]) if item else None
        return reader.get_destination_page_number(item) + 1
    except Exception:
        return None


def parse_sequence(reader: PdfReader, items: list[Any], depth: int = 0) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for item in items:
        # pypdf's outline is a mixed sequence: a node followed by a list that
        # contains its children. The list belongs to the previous node.
        if isinstance(item, list):
            if nodes:
                nodes[-1]["children"] = parse_sequence(reader, item, depth + 1)
            continue
        try:
            raw_title = str(item.title)
        except Exception:
            continue
        page = destination_page(reader, item)
        if page is None:
            continue
        node = {
            "raw_title": normalize_space(raw_title),
            "start_pdf_page": page,
            "level": depth,
            "children": [],
        }
        nodes.append(node)
    return nodes


def decorate(
    nodes: list[dict[str, Any]],
    parent: dict[str, Any] | None = None,
    chapter: int | str | None = None,
) -> None:
    for index, node in enumerate(nodes):
        parsed = parse_heading(node["raw_title"])
        kind = parsed["kind"]
        number = parsed["number"]
        title = parsed["title"]
        node_chapter = parsed["chapter"]
        if node_chapter is None:
            node_chapter = chapter

        if kind == "chapter":
            section = str(number)
        elif kind == "appendix":
            section = str(number)
        elif kind == "section" or kind == "subsection":
            section = str(number)
        elif kind == "summary":
            section = f"{node_chapter}-summary"
        elif kind == "exercises":
            section = f"{node_chapter}-exercises"
        else:
            section = str(index + 1)

        node["section"] = section
        node["title"] = title
        node["kind"] = kind
        node["chapter"] = node_chapter
        node["start_book_page"] = book_page(node["start_pdf_page"])
        node["parent_section"] = parent.get("section") if parent else None
        if kind in {"chapter", "appendix"}:
            node["chapter_title"] = title
        elif parent:
            node["chapter_title"] = parent.get("chapter_title")
        else:
            node["chapter_title"] = None
        decorate(node["children"], node, node_chapter)


def assign_end_pages(nodes: list[dict[str, Any]], default_end: int) -> None:
    for index, node in enumerate(nodes):
        if index + 1 < len(nodes):
            end = int(nodes[index + 1]["start_pdf_page"]) - 1
        else:
            end = default_end
        node["end_pdf_page"] = max(int(node["start_pdf_page"]), end)
        node["end_book_page"] = book_page(node["end_pdf_page"])
        assign_end_pages(node["children"], node["end_pdf_page"])


def flatten(
    nodes: list[dict[str, Any]],
    parent_id: str | None = None,
    result: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    result = result if result is not None else []
    for node in nodes:
        row = {key: value for key, value in node.items() if key != "children"}
        row["parent_section"] = parent_id
        row["children_sections"] = [child["section"] for child in node["children"]]
        result.append(row)
        flatten(node["children"], row["section"], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=None)
    args = parser.parse_args()
    ensure_dirs()
    pdf = args.pdf or source_pdf_path()
    if not pdf.is_file():
        fail(f"PDF not found: {pdf}")

    reader = PdfReader(str(pdf))
    if len(reader.pages) != EXPECTED_PAGE_COUNT:
        fail(f"unexpected page count: {len(reader.pages)} != {EXPECTED_PAGE_COUNT}")

    roots = parse_sequence(reader, list(reader.outline))
    if not roots:
        fail("PDF outline is empty")
    decorate(roots)
    assign_end_pages(roots, len(reader.pages))

    # Keep only the real book structure. Front matter stays in outline.json but
    # is not turned into section Markdown.
    book_roots = [node for node in roots if node["kind"] in {"chapter", "appendix"}]
    if not book_roots:
        fail("no chapter/appendix nodes in outline")

    sections = flatten(book_roots)
    for row in sections:
        row["start_book_page"] = book_page(row["start_pdf_page"])
        row["end_book_page"] = book_page(row["end_pdf_page"])

    outline = {
        "source_pdf": str(pdf),
        "page_count": len(reader.pages),
        "book_page_offset": BOOK_PAGE_OFFSET,
        "nodes": roots,
    }
    write_json(WORK_DIR / "outline" / "outline.json", outline)
    write_json(WORK_DIR / "outline" / "sections.json", sections)

    total_nodes = sum(1 for _ in iter_nodes(roots))
    print(f"outline nodes: {total_nodes}")
    print(f"book chapters/appendices: {len(book_roots)}")
    print(f"sections: {len(sections)}")
    for node in book_roots[:3]:
        print(
            f"  {node['raw_title']}: PDF {node['start_pdf_page']} → 教材 {node['start_book_page']}"
        )


def iter_nodes(nodes: list[dict[str, Any]]):
    for node in nodes:
        yield node
        yield from iter_nodes(node["children"])


if __name__ == "__main__":
    main()
