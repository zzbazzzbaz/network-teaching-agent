from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_figures import caption_info  # noqa: E402
from build_sections import html_table_to_markdown  # noqa: E402
from common import book_page, format_pages, parse_heading, plan_output_units  # noqa: E402


def test_page_mapping() -> None:
    assert book_page(12) == 1
    assert book_page(147) == 136
    assert book_page(11) is None
    assert format_pages(136, 141) == "136–141"
    assert format_pages(136, 136) == "136"


def test_heading_parser() -> None:
    chapter = parse_heading("第4章 网络层")
    assert chapter["kind"] == "chapter"
    assert chapter["chapter"] == 4
    section = parse_heading("4.2.5 IP数据报的格式")
    assert section["kind"] == "subsection"
    assert section["number"] == "4.2.5"
    appendix = parse_heading("附录A 部分习题的解答")
    assert appendix["kind"] == "appendix"


def test_table_converter() -> None:
    html = "<table><tr><th>字段</th><th>长度</th></tr><tr><td>版本</td><td>4</td></tr></table>"
    markdown = html_table_to_markdown(html)
    assert "| 字段 | 长度 |" in markdown
    assert "| 版本 | 4 |" in markdown


def test_figure_caption() -> None:
    chapter, number, title = caption_info("图 4-5 IP数据报的格式")
    assert chapter == 4
    assert number == "5"
    assert title == "IP数据报的格式"


def test_plan_units_splits_large_sections() -> None:
    chapters = [
        {
            "section": "1",
            "title": "概述",
            "kind": "chapter",
            "chapter": 1,
            "start_pdf_page": 12,
            "end_pdf_page": 30,
            "start_book_page": 1,
            "end_book_page": 19,
            "children": [
                {
                    "section": "1.1",
                    "title": "小节目",
                    "kind": "section",
                    "chapter": 1,
                    "start_pdf_page": 12,
                    "end_pdf_page": 13,
                    "start_book_page": 1,
                    "end_book_page": 2,
                    "children": [],
                },
                {
                    "section": "1.2",
                    "title": "大节目",
                    "kind": "section",
                    "chapter": 1,
                    "start_pdf_page": 14,
                    "end_pdf_page": 30,
                    "start_book_page": 3,
                    "end_book_page": 19,
                    "children": [
                        {
                            "section": "1.2.1",
                            "title": "子节一",
                            "kind": "subsection",
                            "chapter": 1,
                            "start_pdf_page": 14,
                            "end_pdf_page": 20,
                            "start_book_page": 3,
                            "end_book_page": 9,
                            "children": [],
                        },
                        {
                            "section": "1.2.2",
                            "title": "子节二",
                            "kind": "subsection",
                            "chapter": 1,
                            "start_pdf_page": 21,
                            "end_pdf_page": 30,
                            "start_book_page": 10,
                            "end_book_page": 19,
                            "children": [],
                        },
                    ],
                },
            ],
        }
    ]
    units = plan_output_units(chapters)
    sections = [unit["section"] for unit in units]
    assert sections == ["1.1", "1.2.1", "1.2.2"]
    assert units[0]["path"] == "01-概述/1.1-小节目.md"
    assert units[1]["path"] == "01-概述/1.2.1-子节一.md"
