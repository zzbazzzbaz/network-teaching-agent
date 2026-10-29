"""从教材 00-toc.md 生成 knowledge-points.json。

用法（在 apps/api 下）：
    uv run python -m app.scripts.generate_knowledge_points
    uv run python -m app.scripts.generate_knowledge_points --toc ... --output ...
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TOC = (
    API_DIR.parent
    / "agent"
    / "agent"
    / "resources"
    / "skills"
    / "teaching"
    / "computer-networks-textbook"
    / "textbook"
    / "00-toc.md"
)
DEFAULT_OUTPUT = API_DIR / "app" / "data" / "question_bank" / "knowledge-points.json"


def parse_toc(toc_path: Path) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    for line in toc_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("- "):
            continue
        title = text[2:].strip().split("（教材", 1)[0].strip()
        if not title or title in {"本章的重要概念", "习题"} or title.startswith("附录"):
            continue

        chapter = re.match(r"^第(\d+)章\s+(.+)$", title)
        if chapter:
            nodes.append(
                {
                    "id": chapter.group(1),
                    "title": chapter.group(2).strip(),
                    "parent_id": None,
                    "level": 1,
                }
            )
            continue

        section = re.match(r"^(\d+(?:\.\d+)+)\s+(.+)$", title)
        if section:
            node_id = section.group(1)
            level = node_id.count(".") + 1
            parent_id = None if level == 1 else node_id.rsplit(".", 1)[0]
            nodes.append(
                {
                    "id": node_id,
                    "title": section.group(2).strip(),
                    "parent_id": parent_id,
                    "level": level,
                }
            )
            continue

        raise SystemExit(f"无法解析目录行：{line}")

    nodes.append({"id": "99", "title": "综合", "parent_id": None, "level": 0})
    ids = {str(node["id"]) for node in nodes}
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id not in ids:
            raise SystemExit(f"知识点 {node['id']} 的父节点 {parent_id} 不存在")
    return nodes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从教材目录生成知识点 JSON")
    parser.add_argument("--toc", type=Path, default=DEFAULT_TOC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    nodes = parse_toc(args.toc)
    payload = {"version": 1, "course": "computer-networks", "nodes": nodes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已生成 {len(nodes)} 个知识点：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
