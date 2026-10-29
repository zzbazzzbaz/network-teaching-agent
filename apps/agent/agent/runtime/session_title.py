from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Any, NotRequired

from deepagents.graph import DeepAgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.runtime import Runtime

from agent.infra.model import get_llm
from agent.infra.session_api import (
    SessionTitleError,
    SessionTitleNotFound,
    set_session_title,
)
from agent.runtime.prompts import load_prompt

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TITLE = "新会话"
MAX_TITLE_LENGTH = 24
MAX_SOURCE_CHARS = 1200
TITLE_TIMEOUT_SECONDS = 8


class SessionTitleState(DeepAgentState):
    session_title_generated: NotRequired[bool]


class SessionTitleMiddleware(AgentMiddleware[SessionTitleState, None, Any]):
    name = "session_title"
    state_schema = SessionTitleState

    async def aafter_agent(
        self,
        state: SessionTitleState,
        runtime: Runtime[None],
    ) -> dict[str, Any] | None:
        if state.get("session_title_generated"):
            return None

        messages = state.get("messages") or []
        human_text = _first_text(messages, HumanMessage)
        if not human_text:
            return None

        assistant_text = _first_text(messages, AIMessage)

        try:
            config = get_config()
            configurable = config["configurable"]
            user_id = str(configurable["langgraph_auth_user_id"])
            thread_id = str(configurable["thread_id"])
        except Exception as e:
            logger.warning("会话标题跳过：缺少运行身份 error=%s", type(e).__name__)
            return None

        title = await _generate_title(
            human_text=human_text,
            assistant_text=assistant_text,
            thread_id=thread_id,
            config=config,
        )
        if title is None:
            return None

        try:
            result = await set_session_title(
                user_id=user_id,
                thread_id=thread_id,
                title=title,
            )
        except SessionTitleNotFound:
            logger.info("会话标题跳过：会话不存在 thread_id=%s", thread_id)
            return {"session_title_generated": True}
        except SessionTitleError as e:
            logger.warning(
                "会话标题写入失败 thread_id=%s error=%s",
                thread_id,
                type(e).__name__,
            )
            return None

        logger.info(
            "会话标题已处理 thread_id=%s updated=%s reason=%s title_len=%s",
            thread_id,
            result.updated,
            result.reason,
            len(result.title),
        )
        return {"session_title_generated": True}


def _first_text(
    messages: Sequence[BaseMessage],
    message_type: type[BaseMessage],
) -> str:
    for message in messages:
        if not isinstance(message, message_type):
            continue
        text = message.text.strip()
        if text:
            return text
    return ""


async def _generate_title(
    *,
    human_text: str,
    assistant_text: str,
    thread_id: str,
    config: RunnableConfig,
) -> str | None:
    payload = _title_payload(human_text, assistant_text)
    # 标题只是短文本，关掉思考：否则 reasoning 会吃掉 max_tokens，正文为空。
    llm = get_llm().bind(
        reasoning_effort="none",
        max_tokens=64,
        temperature=0,
    )

    try:
        response = await asyncio.wait_for(
            llm.ainvoke(
                [
                    SystemMessage(content=load_prompt("title")),
                    HumanMessage(content=payload),
                ],
                config=config,
            ),
            timeout=TITLE_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.warning(
            "会话标题生成失败 thread_id=%s error=%s",
            thread_id,
            type(e).__name__,
        )
        return None

    title = _sanitize_title(response.text)
    if title is None:
        metadata = response.response_metadata or {}
        usage = metadata.get("token_usage") or {}
        details = usage.get("completion_tokens_details") or {}
        logger.warning(
            "会话标题为空或无效 thread_id=%s finish=%s raw_len=%s reasoning_tokens=%s",
            thread_id,
            metadata.get("finish_reason"),
            len(response.text or ""),
            details.get("reasoning_tokens"),
        )
    return title


def _title_payload(human_text: str, assistant_text: str) -> str:
    return (
        "<student>\n"
        f"{human_text[:MAX_SOURCE_CHARS]}\n"
        "</student>\n\n"
        "<assistant>\n"
        f"{assistant_text[:MAX_SOURCE_CHARS]}\n"
        "</assistant>"
    )


def _sanitize_title(raw: str) -> str | None:
    text = raw.strip().splitlines()[0] if raw.strip() else ""
    text = re.sub(r"^(会话)?标题[：:]\s*", "", text)
    text = text.strip(" \t\"'“”‘’《》<>()（）[]【】")
    text = re.sub(r"[。！？!?；;：:，,、\s]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or text == DEFAULT_SESSION_TITLE:
        return None
    if len(text) < 2:
        return None
    return text[:MAX_TITLE_LENGTH].strip() or None
