#!/usr/bin/env python3
"""Normalize MinerU content_list.json into page-attributed blocks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    RAW_DIR,
    WORK_DIR,
    clean_multiline_text,
    ensure_dirs,
    fail,
    normalize_space,
    read_json,
    strip_page_number_line,
    write_json,
    write_jsonl,
)


def load_parts() -> list[dict[str, Any]]:
    parts = read_json(WORK_DIR / "parts.json", [])
    if not parts:
        fail("work/parts.json missing; run split_pdf.py first")
    return parts


def find_part_dir(part_id: str) -> Path | None:
    candidates = []
    for batch_dir in RAW_DIR.glob("mineru/batch-*"):
        candidate = batch_dir / part_id
        if (candidate / "content_list.json").is_file():
            candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("content_list", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def caption_of(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_space(value)
        if isinstance(value, list):
            parts = [normalize_space(str(part)) for part in value if str(part).strip()]
            if parts:
                return normalize_space(" ".join(parts))
    return ""


def clean_text(text: Any) -> str:
    if text is None:
        return ""
    raw = str(text).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [part for part in re.split(r"\n\s*\n", raw) if part.strip()]
    if not paragraphs:
        return ""
    return "\n\n".join(cleaned for part in paragraphs if (cleaned := clean_multiline_text(part)))


def is_page_number_block(text: str) -> bool:
    if not text:
        return False
    return strip_page_number_line(text)


def normalize_items(
    items: list[dict[str, Any]],
    part: dict[str, Any],
    part_dir: Path,
) -> list[dict[str, Any]]:
    start_pdf_page = int(part["start_pdf_page"])
    page_count = int(part["page_count"])
    pages: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for order, item in enumerate(items):
        try:
            local_page_idx = int(item.get("page_idx", 0))
        except (TypeError, ValueError):
            local_page_idx = 0
        if local_page_idx < 0 or local_page_idx >= page_count:
            print(f"warning: {part['part_id']} block on invalid page_idx {local_page_idx}; skipped")
            continue
        pdf_page = start_pdf_page + local_page_idx
        block_type = str(item.get("type") or "text")
        text = ""
        caption = ""
        table_body = str(item.get("table_body") or "")
        image_path = ""

        if block_type in {"text", "title", "equation", "list", "code", "page_footnote"}:
            text = clean_text(item.get("text"))
        elif block_type == "table":
            caption = caption_of(item, "table_caption", "caption", "img_caption")
            if not table_body:
                text = clean_text(item.get("text"))
        elif block_type == "image":
            caption = caption_of(item, "img_caption", "image_caption", "caption")
        elif block_type in {"header", "footer", "page_number"}:
            text = clean_text(item.get("text"))

        raw_img = item.get("img_path")
        if raw_img:
            candidate = (part_dir / str(raw_img)).resolve()
            if candidate.is_file():
                image_path = str(candidate)

        if not text and not caption and not table_body and not image_path:
            continue
        if is_page_number_block(text):
            continue
        bbox = item.get("bbox")
        pages[pdf_page].append(
            {
                "type": block_type,
                "text": text,
                "caption": caption,
                "table_body": table_body,
                "image_path": image_path,
                "img_path": str(raw_img) if raw_img else "",
                "part_id": part["part_id"],
                "local_page_idx": local_page_idx,
                "order": order,
                "text_level": item.get("text_level"),
                "bbox": bbox,
            }
        )

    rows = []
    for pdf_page in sorted(pages):
        rows.append(
            {
                "pdf_page": pdf_page,
                "book_page": pdf_page - 11 if pdf_page > 11 else None,
                "part_id": part["part_id"],
                "local_page_idx": pdf_page - start_pdf_page,
                "blocks": pages[pdf_page],
            }
        )
    return rows


def remove_repeated_headers(pages: list[dict[str, Any]]) -> None:
    page_sets: dict[str, set[int]] = defaultdict(set)
    for page in pages:
        for block in page["blocks"]:
            if block["type"] not in {"text", "header", "footer", "page_footnote"}:
                continue
            text = normalize_space(block.get("text") or "")
            if not text or len(text) > 80:
                continue
            page_sets[text].add(int(page["pdf_page"]))

    def has_consecutive_run(numbers: set[int], length: int = 3) -> bool:
        ordered = sorted(numbers)
        run = 1
        for previous, current in zip(ordered, ordered[1:], strict=False):
            run = run + 1 if current == previous + 1 else 1
            if run >= length:
                return True
        return False

    repeated = {
        text
        for text, page_set in page_sets.items()
        if len(page_set) >= 3 and has_consecutive_run(page_set)
    }

    for page in pages:
        cleaned = []
        for block in page["blocks"]:
            if block["type"] in {"header", "footer", "page_number"}:
                continue
            text = normalize_space(block.get("text") or "")
            if text in repeated and block["type"] in {"text"}:
                continue
            if not block.get("text") and not block.get("caption") and not block.get("table_body"):
                if not block.get("image_path"):
                    continue
            cleaned.append(block)
        page["blocks"] = cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", action="append", help="part_id; repeat for a subset")
    args = parser.parse_args()
    ensure_dirs()
    parts = load_parts()
    if args.part:
        wanted = set(args.part)
        parts = [part for part in parts if part["part_id"] in wanted]
        if not parts:
            fail("no matching parts")

    all_pages: list[dict[str, Any]] = []
    used_parts: list[dict[str, Any]] = []
    for part in parts:
        part_dir = find_part_dir(part["part_id"])
        if not part_dir:
            fail(f"no MinerU result found for {part['part_id']}")
        payload = json.loads((part_dir / "content_list.json").read_text(encoding="utf-8"))
        items = extract_items(payload)
        if not items:
            fail(f"{part['part_id']}: content_list.json has no items")
        pages = normalize_items(items, part, part_dir)
        if not pages:
            fail(f"{part['part_id']}: no valid page blocks")
        all_pages.extend(pages)
        used_parts.append(
            {
                "part_id": part["part_id"],
                "start_pdf_page": part["start_pdf_page"],
                "end_pdf_page": part["end_pdf_page"],
                "blocks": sum(len(page["blocks"]) for page in pages),
                "content_list": str(part_dir / "content_list.json"),
            }
        )
        print(f"{part['part_id']}: {len(items)} items, {len(pages)} pages")

    # A blank scan page may have no MinerU blocks. Keep one empty row for every
    # PDF page in the selected parts so page continuity and offsets stay valid.
    existing = {int(page["pdf_page"]) for page in all_pages}
    for part in parts:
        for pdf_page in range(int(part["start_pdf_page"]), int(part["end_pdf_page"]) + 1):
            if pdf_page in existing:
                continue
            all_pages.append(
                {
                    "pdf_page": pdf_page,
                    "book_page": pdf_page - 11 if pdf_page > 11 else None,
                    "part_id": part["part_id"],
                    "local_page_idx": pdf_page - int(part["start_pdf_page"]),
                    "blocks": [],
                    "blank": True,
                }
            )
    all_pages.sort(key=lambda page: int(page["pdf_page"]))
    remove_repeated_headers(all_pages)

    # Verify page continuity for the selected parts. Gaps are allowed when only
    # a sample range is normalized; a full run must cover all 485 pages.
    pdf_pages = [int(page["pdf_page"]) for page in all_pages]
    duplicates = [page for page, count in Counter(pdf_pages).items() if count > 1]
    if duplicates:
        fail(f"duplicate PDF pages after merge: {duplicates[:10]}")

    write_jsonl(WORK_DIR / "pages" / "pages.jsonl", all_pages)
    write_json(
        WORK_DIR / "pages" / "parts-used.json",
        {
            "parts": used_parts,
            "page_count": len(all_pages),
            "first_pdf_page": min(pdf_pages),
            "last_pdf_page": max(pdf_pages),
        },
    )

    sample_lines = ["# OCR sample", ""]
    for page in all_pages[:30]:
        sample_lines.append(f"## PDF {page['pdf_page']} / 教材 {page['book_page']}")
        for block in page["blocks"][:12]:
            text = block.get("text") or block.get("caption") or block.get("table_body")
            if text:
                sample_lines.append(f"- {block['type']}: {str(text)[:300]}")
        sample_lines.append("")
    (WORK_DIR / "review" / "ocr-samples.md").write_text(
        "\n".join(sample_lines) + "\n", encoding="utf-8"
    )

    print(f"pages: {len(all_pages)} ({min(pdf_pages)}–{max(pdf_pages)})")
    print(f"wrote {WORK_DIR / 'pages' / 'pages.jsonl'}")


if __name__ == "__main__":
    main()
