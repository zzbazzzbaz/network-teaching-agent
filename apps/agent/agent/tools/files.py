from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime

from agent.infra.files_api import FileApiError, FileNotFound, get_file_metadata
from agent.runtime.context import tool_context

_DESCRIPTION = (
    "重新加载之前上传、但已经卸载的图片。"
    "当消息里出现“[图片已卸载：<name>，可调用 view_image 重看]”或需要重新查看旧图时调用。"
    "file_id 只能从消息里的“[图片] <name> (file_id=...)”标记中获取，不要猜测或构造。"
)


def make_view_image() -> BaseTool:
    @tool(response_format="content_and_artifact", description=_DESCRIPTION)
    async def view_image(
        *,
        file_id: str,
        runtime: ToolRuntime,
    ) -> tuple[str, dict[str, Any]]:
        try:
            parsed = uuid.UUID(file_id)
        except (TypeError, ValueError, AttributeError):
            return "file_id 格式不正确，无法加载图片。", {"images": []}

        try:
            metadata = await get_file_metadata(
                tool_context(runtime).user_id,
                str(parsed),
            )
        except FileNotFound:
            return "图片不存在或无权访问。", {"images": []}
        except FileApiError:
            return "图片服务暂不可用，请稍后重试。", {"images": []}

        return (
            "已加载图片，图片会附在本次请求中。",
            {"images": [{"file_id": str(parsed), "name": metadata.name}]},
        )

    return view_image
