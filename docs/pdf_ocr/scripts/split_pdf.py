#!/usr/bin/env python3
"""Split the source PDF into API-sized parts, respecting chapter boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    EXPECTED_PAGE_COUNT,
    RAW_DIR,
    WORK_DIR,
    book_page,
    ensure_dirs,
    fail,
    sha256_file,
    source_pdf_path,
    write_json,
)
from pypdf import PdfReader, PdfWriter


def load_chapter_ranges() -> list[dict[str, Any]]:
    outline_path = WORK_DIR / "outline" / "outline.json"
    import json

    if not outline_path.is_file():
        fail("outline.json missing; run extract_outline.py first")
    data = json.loads(outline_path.read_text(encoding="utf-8"))
    ranges = []
    for node in data["nodes"]:
        if node.get("kind") not in {"chapter", "appendix"}:
            continue
        ranges.append(
            {
                "title": node["title"],
                "section": node["section"],
                "start_pdf_page": int(node["start_pdf_page"]),
                "end_pdf_page": int(node["end_pdf_page"]),
            }
        )
    return ranges


def make_parts(
    chapters: list[dict[str, Any]], max_pages: int, total_pages: int
) -> list[dict[str, int]]:
    parts: list[dict[str, int]] = []
    current: dict[str, int] | None = None

    for chapter in chapters:
        start = int(chapter["start_pdf_page"])
        end = int(chapter["end_pdf_page"])
        if end - start + 1 > max_pages:
            if current:
                parts.append(current)
                current = None
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + max_pages - 1, end)
                parts.append({"start_pdf_page": cursor, "end_pdf_page": chunk_end})
                cursor = chunk_end + 1
            continue

        if current is None:
            current = {"start_pdf_page": start, "end_pdf_page": end}
        elif end - current["start_pdf_page"] + 1 <= max_pages:
            current["end_pdf_page"] = end
        else:
            parts.append(current)
            current = {"start_pdf_page": start, "end_pdf_page": end}

    if current:
        parts.append(current)

    # The first part should include the cover, title, preface and TOC. The API
    # gets pages 1..N, not just chapter 1.
    if parts:
        parts[0]["start_pdf_page"] = 1
    if parts[-1]["end_pdf_page"] != total_pages:
        parts[-1]["end_pdf_page"] = total_pages

    for part in parts:
        part["page_count"] = part["end_pdf_page"] - part["start_pdf_page"] + 1
    return parts


def part_id(part: dict[str, int]) -> str:
    return f"part-{part['start_pdf_page']:03d}-{part['end_pdf_page']:03d}"


def write_part_pdf(reader: PdfReader, part: dict[str, Any], output: Path) -> None:
    writer = PdfWriter()
    for page_number in range(part["start_pdf_page"], part["end_pdf_page"] + 1):
        writer.add_page(reader.pages[page_number - 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def parse_range(value: str) -> tuple[int, int]:
    match = value.strip()
    if "-" not in match:
        page = int(match)
        return page, page
    start, end = match.split("-", 1)
    return int(start), int(end)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--range", dest="page_range", help="manual sample range, e.g. 12-20")
    parser.add_argument("--part-id", default="sample")
    args = parser.parse_args()
    ensure_dirs()
    pdf = args.pdf or source_pdf_path()
    if not pdf.is_file():
        fail(f"PDF not found: {pdf}")

    reader = PdfReader(str(pdf))
    if len(reader.pages) != EXPECTED_PAGE_COUNT:
        fail(f"unexpected page count: {len(reader.pages)} != {EXPECTED_PAGE_COUNT}")

    if args.page_range:
        start, end = parse_range(args.page_range)
        if not (1 <= start <= end <= len(reader.pages)):
            fail(f"invalid range: {args.page_range}")
        parts = [
            {
                "start_pdf_page": start,
                "end_pdf_page": end,
                "page_count": end - start + 1,
            }
        ]
        manual = True
    else:
        chapters = load_chapter_ranges()
        parts = make_parts(chapters, args.max_pages, len(reader.pages))
        manual = False

    manifest = []
    for part in parts:
        part_name = args.part_id if manual else part_id(part)
        if manual:
            part_name = f"{args.part_id}-{start:03d}-{end:03d}"
        output = RAW_DIR / "split" / f"{part_name}.pdf"
        write_part_pdf(reader, part, output)
        row = {
            "part_id": part_name,
            "start_pdf_page": part["start_pdf_page"],
            "end_pdf_page": part["end_pdf_page"],
            "page_count": part["page_count"],
            "start_book_page": book_page(part["start_pdf_page"]),
            "end_book_page": book_page(part["end_pdf_page"]),
            "file": str(output),
            "sha256": sha256_file(output),
            "source_pdf": str(pdf),
        }
        manifest.append(row)
        print(
            f"{part_name}: PDF {row['start_pdf_page']}–{row['end_pdf_page']} "
            f"({row['page_count']} pages) → {output.name}"
        )

    write_json(WORK_DIR / "parts.json", manifest)
    print(f"wrote {WORK_DIR / 'parts.json'} ({len(manifest)} parts)")


if __name__ == "__main__":
    main()
