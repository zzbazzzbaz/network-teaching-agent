#!/usr/bin/env python3
"""Validate page mapping, Markdown frontmatter and generated indexes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import (
    EXPECTED_PAGE_COUNT,
    GENERATED_DIR,
    KNOWN_PAGE_MAPPINGS,
    WORK_DIR,
    ensure_dirs,
    fail,
    read_json,
    read_jsonl,
)


def parse_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    data: dict[str, Any] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[key.strip()] = value
    return data


def parse_pages(value: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"\[(\d+),\s*(\d+)\]", value)
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        return None
    return start, end


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=GENERATED_DIR / "computer-networks")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    errors: list[str] = []
    warnings: list[str] = []

    pages = read_jsonl(WORK_DIR / "pages" / "pages.jsonl")
    if not pages:
        fail("pages.jsonl missing")
    pdf_pages = [int(page["pdf_page"]) for page in pages]
    if len(pdf_pages) != len(set(pdf_pages)):
        errors.append("pages.jsonl has duplicate PDF pages")
    if pdf_pages != sorted(pdf_pages):
        errors.append("pages.jsonl is not sorted")
    if not args.allow_partial:
        if min(pdf_pages) > 12:
            errors.append(f"pages start at {min(pdf_pages)}, expected 12 or earlier")
        if max(pdf_pages) < EXPECTED_PAGE_COUNT:
            errors.append(f"pages end at {max(pdf_pages)}, expected {EXPECTED_PAGE_COUNT}")
        if len(pdf_pages) < EXPECTED_PAGE_COUNT - 10:
            errors.append(f"only {len(pdf_pages)} pages normalized")

    page_map = {int(page["pdf_page"]): page.get("book_page") for page in pages}
    for pdf_page, expected_book in KNOWN_PAGE_MAPPINGS.items():
        actual = page_map.get(pdf_page)
        if actual != expected_book:
            message = f"page mapping PDF {pdf_page}: expected {expected_book}, got {actual}"
            if args.allow_partial and actual is None:
                warnings.append(message)
            else:
                errors.append(message)

    units_data = read_json(WORK_DIR / "units.json")
    if not units_data:
        fail("units.json missing")
    units = units_data.get("units", [])
    if len(units) < 100:
        errors.append(f"too few units: {len(units)}")
    paths: set[str] = set()
    for unit in units:
        path = args.skill_root / "textbook" / str(unit["path"])
        if not path.is_file():
            errors.append(f"missing unit file: {path}")
            continue
        if unit["path"] in paths:
            errors.append(f"duplicate unit path: {unit['path']}")
        paths.add(unit["path"])
        front = parse_frontmatter(path)
        if front is None:
            errors.append(f"missing frontmatter: {path}")
            continue
        if "pdf_pages" in front:
            errors.append(f"pdf_pages must not appear in skill frontmatter: {path}")
        if front.get("section") != str(unit.get("section")):
            errors.append(f"section mismatch: {path}")
        pages_value = front.get("book_pages")
        parsed = parse_pages(str(pages_value or ""))
        if not parsed:
            errors.append(f"invalid book_pages: {path}: {pages_value}")
            continue
        start, end = parsed
        if not (1 <= start <= 474 and 1 <= end <= 474):
            errors.append(f"book page out of range: {path}: {start}–{end}")
        if start > end:
            errors.append(f"book page reversed: {path}: {start}–{end}")
        if unit.get("start_book_page") != start or unit.get("end_book_page") != end:
            errors.append(f"units.json book_pages mismatch: {path}")

    chapters = {unit.get("chapter") for unit in units if isinstance(unit.get("chapter"), int)}
    if not args.allow_partial and chapters != set(range(1, 10)):
        errors.append(f"chapter coverage: {sorted(chapters)}")

    index_path = args.skill_root / "textbook" / "00-index.md"
    if not index_path.is_file():
        errors.append("00-index.md missing")
    else:
        index_text = index_path.read_text(encoding="utf-8")
        links = re.findall(r"`([^`]+\.md)`", index_text)
        for link in links:
            if not (args.skill_root / "textbook" / link).is_file():
                errors.append(f"broken 00-index link: {link}")

    pages_json_path = args.skill_root / "textbook" / "00-pages.json"
    if not pages_json_path.is_file():
        errors.append("00-pages.json missing")
    else:
        payload = json.loads(pages_json_path.read_text(encoding="utf-8"))
        sections = payload.get("sections", [])
        if len(sections) != len(units):
            errors.append("00-pages.json section count != units.json")
        for section in sections:
            if not (args.skill_root / "textbook" / section["path"]).is_file():
                errors.append(f"00-pages.json broken path: {section['path']}")
            value = section.get("book_pages") or []
            if len(value) != 2:
                errors.append(f"00-pages.json invalid book_pages: {section['path']}")

    figures_index = args.skill_root / "figures" / "index.md"
    if figures_index.is_file():
        for link in re.findall(
            r"`([^`]+\.(?:png|jpg|jpeg|webp))`", figures_index.read_text(encoding="utf-8")
        ):
            if not (args.skill_root / "figures" / link).is_file():
                errors.append(f"broken figures/index.md link: {link}")
    else:
        warnings.append("figures/index.md missing")

    image_links = 0
    for path in (args.skill_root / "textbook").rglob("*.md"):
        front = parse_frontmatter(path)
        if front and "pdf_pages" in front:
            errors.append(f"pdf_pages found in {path}")
        text = path.read_text(encoding="utf-8")
        image_pattern = r"!\[(?:[^\]\\]|\\.)*\]\(([^)]+)\)"
        for link in re.findall(image_pattern, text):
            if link.startswith(("http://", "https://")):
                continue
            image_links += 1
            target = (path.parent / link).resolve()
            if not target.is_file():
                errors.append(f"broken body image link: {path}: {link}")
    figure_files = len(list((args.skill_root / "figures").rglob("*.*"))) - 1
    print(f"pages: {len(pages)}")
    print(f"units: {len(units)}")
    print(f"chapters: {sorted(chapters)}")
    print(f"body image links: {image_links}")
    print(f"figure files: {figure_files}")
    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        for error in errors:
            print(f"error: {error}")
        fail(f"{len(errors)} validation error(s)")
    print("validation: OK")


if __name__ == "__main__":
    main()
