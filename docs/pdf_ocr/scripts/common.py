"""Shared paths, page mapping and small helpers for the textbook OCR pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input"
RAW_DIR = ROOT / "raw"
WORK_DIR = ROOT / "work"
GENERATED_DIR = ROOT / "generated"
DEFAULT_PDF = INPUT_DIR / "计算机网络（第8版）(谢希仁).pdf"
LEGACY_PDF = ROOT / "计算机网络（第8版）(谢希仁).pdf"
SLUG_BOOK = "computer-networks"
BOOK_TITLE = "计算机网络（第8版）"
BOOK_AUTHOR = "谢希仁"
BOOK_PAGE_OFFSET = 11
EXPECTED_PAGE_COUNT = 485
FRONT_MATTER_LAST_PDF_PAGE = 11

CHAPTER_DIRS = {
    1: "01-概述",
    2: "02-物理层",
    3: "03-数据链路层",
    4: "04-网络层",
    5: "05-运输层",
    6: "06-应用层",
    7: "07-网络安全",
    8: "08-音频视频服务",
    9: "09-无线网络和移动网络",
}

KNOWN_PAGE_MAPPINGS = {
    12: 1,
    53: 42,
    126: 115,
    147: 136,
    249: 238,
    271: 260,
    301: 290,
    381: 370,
    416: 405,
    456: 445,
    472: 461,
    483: 472,
    485: 474,
}


def load_environment() -> Path | None:
    """Load MINERU_API_KEY without overriding the process environment."""
    candidates: list[Path] = []
    explicit = os.environ.get("PDF_OCR_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend([ROOT / ".env", Path("/ocr_pdf/.env")])
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate
    return None


def source_pdf_path() -> Path:
    configured = os.environ.get("PDF_OCR_INPUT_PDF")
    if configured:
        return Path(configured).expanduser()
    if DEFAULT_PDF.is_file():
        return DEFAULT_PDF
    if LEGACY_PDF.is_file():
        return LEGACY_PDF
    return DEFAULT_PDF


def ensure_dirs() -> None:
    for path in (
        INPUT_DIR,
        RAW_DIR / "split",
        RAW_DIR / "mineru",
        WORK_DIR / "outline",
        WORK_DIR / "pages",
        WORK_DIR / "review",
        GENERATED_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_figure_overrides() -> dict[str, dict[str, str]]:
    """Manual corrections for MinerU caption/asset mismatches."""
    data = read_json(ROOT / "config" / "figure-overrides.json", {})
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def book_page(pdf_page: int | None) -> int | None:
    if pdf_page is None:
        return None
    value = pdf_page - BOOK_PAGE_OFFSET
    return value if value >= 1 else None


def format_pages(start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return "—"
    if start == end:
        return str(start)
    return f"{start}–{end}"


def normalize_space(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def strip_page_number_line(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    return bool(
        re.fullmatch(r"[·•.,，\-—–\s]*\d{1,3}[·•.,，\-—–\s]*", line)
        or re.fullmatch(r"[·•\s]*[ivxlcdm]{1,8}[·•\s]*", line, re.IGNORECASE)
    )


def clean_multiline_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = normalize_space(raw_line)
        if not line:
            continue
        if strip_page_number_line(line):
            continue
        lines.append(line)
    if not lines:
        return ""
    # Chinese OCR often inserts a hard line break inside one sentence. Join
    # CJK-to-CJK boundaries without a space, and keep a space for Latin text.
    result = lines[0]
    for line in lines[1:]:
        left = result[-1] if result else ""
        right = line[0] if line else ""
        if is_cjk(left) and is_cjk(right):
            result += line
        elif left in "，。；：！？、）》」』】" or right in "，。；：！？、）》」』】":
            result += line
        else:
            result += " " + line
    return normalize_space(result)


def is_cjk(char: str) -> bool:
    if not char:
        return False
    code = ord(char)
    return 0x3400 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF or 0x3000 <= code <= 0x303F


def safe_slug(text: str, default: str = "section") -> str:
    text = normalize_space(text)
    text = text.replace("/", "／").replace("\\", "＼")
    text = re.sub(r'[<>:"|?*]', "", text)
    text = text.replace(" ", "-")
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    return text or default


def chapter_dir(chapter: int | str) -> str:
    if isinstance(chapter, int):
        return CHAPTER_DIRS.get(chapter, f"{chapter:02d}-chapter")
    if chapter == "A":
        return "appendices"
    return "appendices"


def parse_heading(raw_title: str) -> dict[str, str | int | None]:
    title = normalize_space(raw_title)
    chapter_match = re.match(r"^第\s*(\d+)\s*章\s*(.*)$", title)
    if chapter_match:
        return {
            "number": chapter_match.group(1),
            "title": normalize_space(chapter_match.group(2)) or title,
            "kind": "chapter",
            "chapter": int(chapter_match.group(1)),
        }
    appendix_match = re.match(r"^附录\s*([A-Za-z])\s*(.*)$", title)
    if appendix_match:
        letter = appendix_match.group(1).upper()
        return {
            "number": letter,
            "title": normalize_space(appendix_match.group(2)) or title,
            "kind": "appendix",
            "chapter": letter,
        }
    numbered_match = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", title)
    if numbered_match:
        number = numbered_match.group(1)
        return {
            "number": number,
            "title": normalize_space(numbered_match.group(2)) or title,
            "kind": "subsection" if number.count(".") >= 2 else "section",
            "chapter": int(number.split(".", 1)[0]),
        }
    if title == "本章的重要概念":
        return {"number": None, "title": title, "kind": "summary", "chapter": None}
    if title == "习题":
        return {"number": None, "title": title, "kind": "exercises", "chapter": None}
    return {"number": None, "title": title, "kind": "part", "chapter": None}


def unit_filename(unit: dict[str, Any]) -> str:
    kind = unit.get("kind")
    if kind == "chapter":
        return f"00-第{unit['chapter']}章-{safe_slug(unit['title'])}.md"
    if kind == "summary":
        return "本章的重要概念.md"
    if kind == "exercises":
        return "习题.md"
    number = unit.get("section") or ""
    title = safe_slug(unit.get("title") or "section")
    if number:
        return f"{number}-{title}.md"
    return f"{title}.md"


def iter_leaf_nodes(nodes: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for node in nodes:
        yield node
        yield from iter_leaf_nodes(node.get("children", []))


def load_pages_by_number() -> dict[int, list[dict[str, Any]]]:
    pages = read_jsonl(WORK_DIR / "pages" / "pages.jsonl")
    return {int(page["pdf_page"]): page.get("blocks", []) for page in pages}


def unit_text(unit: dict[str, Any], pages: dict[int, list[dict[str, Any]]]) -> str:
    chunks: list[str] = []
    for pdf_page in range(int(unit["start_pdf_page"]), int(unit["end_pdf_page"]) + 1):
        for block in pages.get(pdf_page, []):
            text = block.get("text") or block.get("caption") or ""
            if text:
                chunks.append(str(text))
    return "\n".join(chunks)


def plan_output_units(
    chapters: list[dict[str, Any]],
    pages: dict[int, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Turn the outline into Markdown files using the v1 granularity rules."""
    units: list[dict[str, Any]] = []
    pages = pages or {}

    def add_node(node: dict[str, Any], parent: dict[str, Any] | None = None) -> None:
        chapter = node.get("chapter")
        if chapter is None and parent:
            chapter = parent.get("chapter")
        section = node.get("section")
        title = node.get("title") or ""
        kind = node.get("kind") or "section"
        unit = {
            "section": section or "",
            "title": title,
            "kind": kind,
            "chapter": chapter,
            "start_pdf_page": int(node["start_pdf_page"]),
            "end_pdf_page": int(node["end_pdf_page"]),
            "start_book_page": node.get("start_book_page"),
            "end_book_page": node.get("end_book_page"),
            "parent_section": parent.get("section") if parent else None,
            "parent_title": parent.get("title") if parent else None,
            "parent_start_pdf_page": (
                int(parent["start_pdf_page"]) if parent and parent.get("start_pdf_page") else None
            ),
            "chapter_title": parent.get("chapter_title") if parent else node.get("chapter_title"),
        }
        unit["path"] = str(
            Path(chapter_dir(chapter) if chapter is not None else "appendices")
            / unit_filename(unit)
        )
        units.append(unit)

    for chapter in chapters:
        if chapter.get("kind") not in {"chapter", "appendix"}:
            continue
        children = chapter.get("children", [])
        if not children:
            add_node(chapter)
            continue

        first_child_start = int(children[0]["start_pdf_page"])
        if first_child_start > int(chapter["start_pdf_page"]):
            intro = dict(chapter)
            intro["end_pdf_page"] = first_child_start - 1
            intro["end_book_page"] = book_page(intro["end_pdf_page"])
            intro["kind"] = "chapter-intro"
            intro["section"] = str(chapter["section"])
            add_node(intro)

        for child in children:
            child_kind = child.get("kind")
            sub_children = child.get("children", [])
            if child_kind in {"summary", "exercises"} or not sub_children:
                add_node(child, chapter)
                continue

            should_split = int(child["end_pdf_page"]) - int(child["start_pdf_page"]) + 1 > 6
            if not should_split and pages:
                estimated = len(unit_text(child, pages).encode("utf-8"))
                should_split = estimated > 12_000

            if not should_split:
                add_node(child, chapter)
                continue

            first_sub_start = int(sub_children[0]["start_pdf_page"])
            if first_sub_start > int(child["start_pdf_page"]):
                intro = dict(child)
                intro["end_pdf_page"] = first_sub_start - 1
                intro["end_book_page"] = book_page(intro["end_pdf_page"])
                intro["kind"] = "section-intro"
                add_node(intro, chapter)
            for sub in sub_children:
                add_node(sub, child)
    return units


def unit_display_title(unit: dict[str, Any]) -> str:
    section = unit.get("section") or ""
    title = unit.get("title") or ""
    kind = unit.get("kind")
    if kind == "summary":
        return f"第{unit.get('chapter')}章 本章的重要概念"
    if kind == "exercises":
        return f"第{unit.get('chapter')}章 习题"
    if kind == "chapter-intro":
        return f"第{unit.get('chapter')}章 {title}"
    if kind == "appendix":
        return f"附录{section} {title}"
    if kind == "chapter":
        return f"第{unit.get('chapter')}章 {title}"
    if section:
        return f"{section} {title}"
    return title


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)
