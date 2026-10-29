from __future__ import annotations

import asyncio
import base64
import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from deepagents.graph import DeepAgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.config import get_config

from agent.infra.files_api import (
    FileApiError,
    FileMetadata,
    FileNotFound,
    get_file_metadata,
    get_file_raw,
)

logger = logging.getLogger(__name__)

MAX_TURNS = 3
MAX_IMAGES_PER_TURN = 3
MAX_TOTAL_IMAGES = 6
MAX_TOTAL_BYTES = 6 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 20

CACHE_MAX_BYTES = 32 * 1024 * 1024
CACHE_TTL_SECONDS = 30 * 60
IMAGE_DETAIL = "original"


@dataclass(frozen=True)
class AttachmentRef:
    file_id: uuid.UUID
    name: str


@dataclass(frozen=True)
class ImagePayload:
    mime: str
    data_url: str
    size_bytes: int


@dataclass
class _CacheEntry:
    payload: ImagePayload
    expires_at: float

    @property
    def cost(self) -> int:
        return len(self.payload.data_url)


@dataclass
class _ResolvedRef:
    ref: AttachmentRef
    payload: ImagePayload | None = None
    metadata: FileMetadata | None = None
    error: str | None = None
    cache_hit: bool = False
    skip_reason: str | None = None
    selected: bool = False

    @property
    def size_bytes(self) -> int | None:
        if self.payload is not None:
            return self.payload.size_bytes
        if self.metadata is not None:
            return self.metadata.size_bytes
        return None


_CACHE: OrderedDict[tuple[str, str], _CacheEntry] = OrderedDict()
_CACHE_BYTES = 0
_CACHE_LOCK = threading.Lock()


def clear_image_cache() -> None:
    global _CACHE_BYTES

    with _CACHE_LOCK:
        _CACHE.clear()
        _CACHE_BYTES = 0


def _cache_get(user_id: str, file_id: uuid.UUID) -> ImagePayload | None:
    global _CACHE_BYTES

    key = (user_id, str(file_id))
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        if entry.expires_at <= now:
            _CACHE_BYTES -= entry.cost
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return entry.payload


def _cache_put(user_id: str, file_id: uuid.UUID, payload: ImagePayload) -> None:
    global _CACHE_BYTES

    cost = len(payload.data_url)
    if cost > CACHE_MAX_BYTES:
        return

    key = (user_id, str(file_id))
    with _CACHE_LOCK:
        previous = _CACHE.pop(key, None)
        if previous is not None:
            _CACHE_BYTES -= previous.cost
        _CACHE[key] = _CacheEntry(
            payload=payload,
            expires_at=time.monotonic() + CACHE_TTL_SECONDS,
        )
        _CACHE_BYTES += cost
        while _CACHE_BYTES > CACHE_MAX_BYTES and _CACHE:
            _, evicted = _CACHE.popitem(last=False)
            _CACHE_BYTES -= evicted.cost


def _identity() -> tuple[str, str] | None:
    try:
        configurable = get_config().get("configurable") or {}
        user_id = configurable.get("langgraph_auth_user_id")
        if not user_id:
            raise KeyError("langgraph_auth_user_id")
        return str(user_id), str(configurable.get("thread_id", ""))
    except Exception as e:
        logger.warning("image_injection_skipped reason=no_identity error=%s", type(e).__name__)
        return None


def _parse_refs(message: BaseMessage) -> list[AttachmentRef]:
    raw = (message.additional_kwargs or {}).get("attachments")
    if not isinstance(raw, list):
        return []

    refs: list[AttachmentRef] = []
    for item in raw[:MAX_ATTACHMENTS_PER_MESSAGE]:
        if not isinstance(item, dict):
            continue
        try:
            file_id = uuid.UUID(str(item.get("file_id")))
        except (TypeError, ValueError, AttributeError):
            continue
        name = item.get("name")
        refs.append(
            AttachmentRef(
                file_id=file_id,
                name=(str(name)[:200] if name else str(file_id)),
            )
        )
    return refs


def _tool_refs(messages: Sequence[BaseMessage], last_human_index: int) -> list[AttachmentRef]:
    refs: list[AttachmentRef] = []
    for message in messages[last_human_index + 1 :]:
        if not isinstance(message, ToolMessage):
            continue
        artifact = message.artifact
        if not isinstance(artifact, dict):
            continue
        images = artifact.get("images")
        if not isinstance(images, list):
            continue
        for item in images[:MAX_ATTACHMENTS_PER_MESSAGE]:
            if not isinstance(item, dict):
                continue
            try:
                file_id = uuid.UUID(str(item.get("file_id")))
            except (TypeError, ValueError, AttributeError):
                continue
            name = item.get("name")
            refs.append(
                AttachmentRef(
                    file_id=file_id,
                    name=(str(name)[:200] if name else str(file_id)),
                )
            )
    return refs


async def _resolve_refs(
    user_id: str,
    refs: list[AttachmentRef],
) -> dict[uuid.UUID, _ResolvedRef]:
    unique: dict[uuid.UUID, AttachmentRef] = {}
    for ref in refs:
        unique.setdefault(ref.file_id, ref)

    async def resolve(ref: AttachmentRef) -> _ResolvedRef:
        cached = _cache_get(user_id, ref.file_id)
        if cached is not None:
            return _ResolvedRef(ref=ref, payload=cached, cache_hit=True)
        try:
            metadata = await get_file_metadata(user_id, str(ref.file_id))
        except FileNotFound:
            return _ResolvedRef(ref=ref, error="not_found")
        except FileApiError:
            return _ResolvedRef(ref=ref, error="failed")
        except Exception as e:
            logger.warning(
                "image_metadata_failed file_id=%s error=%s",
                ref.file_id,
                type(e).__name__,
            )
            return _ResolvedRef(ref=ref, error="failed")
        return _ResolvedRef(ref=ref, metadata=metadata)

    resolved = await asyncio.gather(*(resolve(ref) for ref in unique.values()))
    return {item.ref.file_id: item for item in resolved}


def _clone_for_ref(template: _ResolvedRef, ref: AttachmentRef) -> _ResolvedRef:
    return _ResolvedRef(
        ref=ref,
        payload=template.payload,
        metadata=template.metadata,
        error=template.error,
        cache_hit=template.cache_hit,
    )


async def _load_payloads(user_id: str, refs: list[_ResolvedRef]) -> None:
    unique: dict[uuid.UUID, _ResolvedRef] = {}
    for ref in refs:
        if ref.selected:
            unique.setdefault(ref.ref.file_id, ref)

    async def load(item: _ResolvedRef) -> None:
        if item.payload is not None:
            return
        try:
            raw, mime = await get_file_raw(user_id, str(item.ref.file_id))
        except FileNotFound:
            item.error = "not_found"
            return
        except FileApiError:
            item.error = "failed"
            return
        except Exception as e:
            logger.warning(
                "image_load_failed file_id=%s error=%s",
                item.ref.file_id,
                type(e).__name__,
            )
            item.error = "failed"
            return
        if not raw:
            item.error = "failed"
            return
        payload = ImagePayload(
            mime=mime,
            data_url=_data_url(mime, raw),
            size_bytes=len(raw),
        )
        item.payload = payload
        _cache_put(user_id, item.ref.file_id, payload)

    await asyncio.gather(*(load(item) for item in unique.values()))

    by_id = {item.ref.file_id: item for item in unique.values()}
    for ref in refs:
        if not ref.selected:
            continue
        source = by_id.get(ref.ref.file_id)
        if source is None:
            continue
        ref.payload = source.payload
        if ref.payload is None:
            ref.error = "failed"


def _data_url(mime: str, raw: bytes) -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _image_block(payload: ImagePayload) -> dict[str, Any]:
    return {
        "type": "image_url",
        "image_url": {"url": payload.data_url, "detail": IMAGE_DETAIL},
    }


def _select(
    resolved: list[_ResolvedRef],
    *,
    remaining_images: int,
    remaining_bytes: int,
) -> tuple[int, int]:
    for item in resolved:
        if item.error is not None:
            continue
        size = item.size_bytes
        if size is None or size <= 0:
            item.skip_reason = "too_large"
            continue
        if size > remaining_bytes:
            item.skip_reason = "too_large"
            continue
        if remaining_images <= 0:
            item.skip_reason = "budget"
            continue
        item.selected = True
        remaining_images -= 1
        remaining_bytes -= size
    return remaining_images, remaining_bytes


def _rewrite_human(
    message: AnyMessage,
    *,
    blocks: list[dict[str, Any]],
    notes: list[str],
) -> AnyMessage:
    content = message.content
    if isinstance(content, str):
        parts: list[Any] = [{"type": "text", "text": content}] if content else []
    elif isinstance(content, list):
        parts = list(content)
    else:
        parts = [{"type": "text", "text": str(content)}] if content else []

    parts.extend({"type": "text", "text": note} for note in notes)
    parts.extend(blocks)
    return message.model_copy(update={"content": parts})


class ImageAttachmentMiddleware(AgentMiddleware[DeepAgentState, None, Any]):
    """把最近 3 个用户轮次的图片注入模型请求副本，不改写 state。"""

    name = "image_attachments"

    async def awrap_model_call(
        self,
        request: ModelRequest[None],
        handler: Callable[[ModelRequest[None]], Awaitable[ModelResponse[None]]],
    ) -> ModelCallResult[None]:
        identity = _identity()
        if identity is None:
            return await handler(request)

        user_id, thread_id = identity
        messages = list(request.messages)
        human_indexes = [
            index for index, message in enumerate(messages) if isinstance(message, HumanMessage)
        ]
        if not human_indexes:
            return await handler(request)

        refs_by_human = {index: _parse_refs(messages[index]) for index in human_indexes}
        last_human_index = human_indexes[-1]
        tool_refs = _tool_refs(messages, last_human_index)
        if not any(refs_by_human.values()) and not tool_refs:
            return await handler(request)

        kept_indexes = set(human_indexes[-MAX_TURNS:])

        to_resolve: list[AttachmentRef] = []
        for index in kept_indexes:
            to_resolve.extend(refs_by_human[index][:MAX_IMAGES_PER_TURN])

        resolved_by_id = await _resolve_refs(user_id, to_resolve)

        resolved_by_human: dict[int, list[_ResolvedRef]] = {}
        for index in kept_indexes:
            resolved_by_human[index] = [
                _clone_for_ref(resolved_by_id[ref.file_id], ref)
                for ref in refs_by_human[index][:MAX_IMAGES_PER_TURN]
                if ref.file_id in resolved_by_id
            ]

        remaining_images = MAX_TOTAL_IMAGES
        remaining_bytes = MAX_TOTAL_BYTES
        for index in reversed([item for item in human_indexes if item in kept_indexes]):
            remaining_images, remaining_bytes = _select(
                resolved_by_human[index],
                remaining_images=remaining_images,
                remaining_bytes=remaining_bytes,
            )

        selected_current_ids = {
            item.ref.file_id
            for item in resolved_by_human[last_human_index]
            if item.selected
        }
        filtered_tool_refs: list[AttachmentRef] = []
        seen_tool: set[uuid.UUID] = set()
        for ref in tool_refs:
            if ref.file_id in selected_current_ids or ref.file_id in seen_tool:
                continue
            seen_tool.add(ref.file_id)
            filtered_tool_refs.append(ref)

        tool_resolved: list[_ResolvedRef] = []
        if filtered_tool_refs:
            tool_resolved_by_id = await _resolve_refs(user_id, filtered_tool_refs)
            tool_resolved = [
                _clone_for_ref(tool_resolved_by_id[ref.file_id], ref)
                for ref in filtered_tool_refs
                if ref.file_id in tool_resolved_by_id
            ]
        remaining_images, remaining_bytes = _select(
            tool_resolved,
            remaining_images=remaining_images,
            remaining_bytes=remaining_bytes,
        )

        selected = [item for values in resolved_by_human.values() for item in values if item.selected]
        selected.extend(item for item in tool_resolved if item.selected)
        await _load_payloads(user_id, selected)

        provided_by_tool = {
            item.ref.file_id
            for item in tool_resolved
            if item.selected and item.payload is not None
        }
        blocks_by_human: dict[int, list[dict[str, Any]]] = {}
        notes_by_human: dict[int, list[str]] = {}

        for index in human_indexes:
            refs = refs_by_human[index]
            if not refs:
                continue
            notes = notes_by_human.setdefault(index, [])
            if index not in kept_indexes:
                notes.extend(
                    f"[图片已卸载：{ref.name}，可调用 view_image 重看]" for ref in refs
                )
                continue

            blocks = blocks_by_human.setdefault(index, [])
            extra_refs = refs[MAX_IMAGES_PER_TURN:]
            unloaded = len(extra_refs) - sum(
                1 for ref in extra_refs if ref.file_id in provided_by_tool
            )
            for item in resolved_by_human.get(index, []):
                if item.ref.file_id in provided_by_tool:
                    continue
                if item.error == "not_found":
                    notes.append("[图片不可用]")
                    logger.info(
                        "image_skipped thread_id=%s file_id=%s reason=not_found",
                        thread_id,
                        item.ref.file_id,
                    )
                elif item.error is not None:
                    notes.append("[图片加载失败]")
                    logger.info(
                        "image_skipped thread_id=%s file_id=%s reason=failed",
                        thread_id,
                        item.ref.file_id,
                    )
                elif item.selected and item.payload is not None:
                    blocks.append(_image_block(item.payload))
                    logger.info(
                        "image_injected thread_id=%s file_id=%s bytes=%s cache=%s",
                        thread_id,
                        item.ref.file_id,
                        item.payload.size_bytes,
                        "hit" if item.cache_hit else "miss",
                    )
                elif item.skip_reason == "too_large":
                    notes.append("[图片过大，未加载]")
                    logger.info(
                        "image_skipped thread_id=%s file_id=%s reason=too_large",
                        thread_id,
                        item.ref.file_id,
                    )
                else:
                    unloaded += 1
            if unloaded > 0:
                notes.append(f"[还有 {unloaded} 张图片未加载]")

        tool_index = last_human_index
        tool_blocks = blocks_by_human.setdefault(tool_index, [])
        tool_notes = notes_by_human.setdefault(tool_index, [])
        tool_unloaded = 0
        for item in tool_resolved:
            if item.error == "not_found":
                tool_notes.append("[图片不可用]")
                logger.info(
                    "image_skipped thread_id=%s file_id=%s reason=not_found source=tool",
                    thread_id,
                    item.ref.file_id,
                )
            elif item.error is not None:
                tool_notes.append("[图片加载失败]")
                logger.info(
                    "image_skipped thread_id=%s file_id=%s reason=failed source=tool",
                    thread_id,
                    item.ref.file_id,
                )
            elif item.selected and item.payload is not None:
                tool_blocks.append(_image_block(item.payload))
                logger.info(
                    "image_injected thread_id=%s file_id=%s bytes=%s cache=%s source=tool",
                    thread_id,
                    item.ref.file_id,
                    item.payload.size_bytes,
                    "hit" if item.cache_hit else "miss",
                )
            elif item.skip_reason == "too_large":
                tool_notes.append("[图片过大，未加载]")
                logger.info(
                    "image_skipped thread_id=%s file_id=%s reason=too_large source=tool",
                    thread_id,
                    item.ref.file_id,
                )
            else:
                tool_unloaded += 1
        if tool_unloaded > 0:
            tool_notes.append(f"[还有 {tool_unloaded} 张图片未加载]")

        if not blocks_by_human and not notes_by_human:
            return await handler(request)

        rewritten: list[AnyMessage] = []
        for index, message in enumerate(messages):
            blocks = blocks_by_human.get(index, [])
            notes = notes_by_human.get(index, [])
            if not blocks and not notes:
                rewritten.append(message)
            else:
                rewritten.append(_rewrite_human(message, blocks=blocks, notes=notes))

        return await handler(request.override(messages=rewritten))
