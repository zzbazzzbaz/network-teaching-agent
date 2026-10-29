from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.exceptions import UnprocessableError

KNOWLEDGE_POINTS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "question_bank" / "knowledge-points.json"
)


@dataclass(frozen=True)
class KnowledgePoint:
    id: str
    title: str
    parent_id: str | None
    level: int


@lru_cache
def _load_payload() -> dict[str, object]:
    try:
        payload = json.loads(KNOWLEDGE_POINTS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise RuntimeError(f"知识点文件不存在：{KNOWLEDGE_POINTS_PATH}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"知识点文件不是合法 JSON：{KNOWLEDGE_POINTS_PATH}") from e
    if not isinstance(payload, dict):
        raise RuntimeError("知识点文件根节点必须是对象")
    return payload


@lru_cache
def _load() -> dict[str, KnowledgePoint]:
    payload = _load_payload()
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("知识点文件缺少 nodes 数组")

    result: dict[str, KnowledgePoint] = {}
    for item in nodes:
        if not isinstance(item, dict):
            raise RuntimeError("知识点节点必须是对象")
        node = KnowledgePoint(
            id=str(item["id"]),
            title=str(item["title"]),
            parent_id=None if item.get("parent_id") is None else str(item["parent_id"]),
            level=int(item["level"]),
        )
        if node.id in result:
            raise RuntimeError(f"知识点 ID 重复：{node.id}")
        result[node.id] = node

    for node in result.values():
        if node.parent_id is not None and node.parent_id not in result:
            raise RuntimeError(f"知识点 {node.id} 的父节点 {node.parent_id} 不存在")

    for node in result.values():
        seen: set[str] = set()
        current = node
        while current.parent_id is not None:
            if current.id in seen:
                raise RuntimeError(f"知识点目录存在环：{node.id}")
            seen.add(current.id)
            parent = result.get(current.parent_id)
            if parent is None:
                break
            current = parent
    return result


@lru_cache
def knowledge_point_parents() -> dict[str, str | None]:
    return {node_id: node.parent_id for node_id, node in _load().items()}


def knowledge_points_payload() -> dict[str, object]:
    return _load_payload()


def has_knowledge_point_prefix(prefix: str) -> bool:
    return any(
        node.id == prefix or node.id.startswith(f"{prefix}.")
        for node in _load().values()
    )


def get_knowledge_point(knowledge_point_id: str) -> KnowledgePoint | None:
    return _load().get(knowledge_point_id)


def knowledge_point_title(knowledge_point_id: str) -> str:
    node = get_knowledge_point(knowledge_point_id)
    return node.title if node is not None else knowledge_point_id


def validate_knowledge_points(
    primary_knowledge_point_id: str,
    secondary_knowledge_point_ids: list[str],
) -> None:
    """校验一主多辅知识点；非法 ID 或组合抛 422。"""
    if primary_knowledge_point_id not in _load():
        raise UnprocessableError(
            f"主知识点不存在：{primary_knowledge_point_id}；请使用教材目录编号（如 5.8.2）"
        )
    if len(secondary_knowledge_point_ids) > 3:
        raise UnprocessableError("辅知识点最多 3 个")
    seen: set[str] = set()
    for knowledge_point_id in secondary_knowledge_point_ids:
        if knowledge_point_id == primary_knowledge_point_id:
            raise UnprocessableError("辅知识点不能包含主知识点")
        if knowledge_point_id in seen:
            raise UnprocessableError(f"辅知识点重复：{knowledge_point_id}")
        seen.add(knowledge_point_id)
        if knowledge_point_id not in _load():
            raise UnprocessableError(
                f"辅知识点不存在：{knowledge_point_id}；请使用教材目录编号（如 5.8.2）"
            )


def clear_cache() -> None:
    """仅供测试或教材改版后显式刷新。"""
    _load.cache_clear()
    _load_payload.cache_clear()
    knowledge_point_parents.cache_clear()
