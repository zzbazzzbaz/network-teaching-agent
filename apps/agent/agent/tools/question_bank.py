from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime

from agent.infra.question_bank_api import (
    QuestionBankApiError,
    user_id_from_config,
)
from agent.infra.question_bank_api import (
    save_question as save_question_api,
)
from agent.infra.question_bank_api import (
    search_questions as search_questions_api,
)
from agent.tools.schemas.question_bank import (
    QuestionDetail,
    QuestionScope,
    QuestionType,
    SaveQuestionInput,
    SearchQuestionsInput,
)

_SEARCH_DESCRIPTION = (
    "搜索公共题库和当前学生的私有题库。默认 scope=all；summary 不返回答案，"
    "full 最多 3 条且包含参考答案。一次最多展示 10 道题，不要把题库全文贴给学生。"
)
_SAVE_DESCRIPTION = (
    "把学生明确要求保存的题目加入学生自己的私有题库。只创建私有题，不发布公共题，"
    "不做去重。只在学生说“记下来/加入题库”时调用。"
)


def _format_search(payload: dict[str, Any]) -> str:
    items = payload.get("items")
    total = payload.get("total")
    if not isinstance(items, list) or not items:
        return "没有找到符合条件的题目。"
    lines = [f"共 {total} 条，当前显示 {len(items)} 条。"]
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        origin = item.get("origin", "mine")
        question_type = item.get("question_type", "")
        primary = item.get("primary_knowledge_point")
        primary_id = primary.get("id") if isinstance(primary, dict) else ""
        primary_title = primary.get("title") if isinstance(primary, dict) else ""
        lines.append(
            f"{index}. [{origin}] {question_type} · {primary_id} {primary_title}".rstrip()
        )
        secondary = item.get("secondary_knowledge_points")
        if isinstance(secondary, list) and secondary:
            labels = [
                f"{point.get('id')} {point.get('title')}"
                for point in secondary
                if isinstance(point, dict)
            ]
            if labels:
                lines.append("   辅知识点：" + "、".join(labels))
        preview = item.get("stem_preview")
        if isinstance(preview, str):
            lines.append(f"   摘要：{preview}")
        stem = item.get("stem")
        if isinstance(stem, str) and stem:
            lines.append(f"   题干：{stem}")
        options = item.get("options")
        if isinstance(options, list) and options:
            lines.append("   选项：" + " | ".join(str(option) for option in options))
        correct_option = item.get("correct_option")
        if isinstance(correct_option, str) and correct_option:
            lines.append(f"   参考答案：{correct_option}（仅用于讲解，不要直接展示给学生）")
        reference_answer = item.get("reference_answer")
        if isinstance(reference_answer, str) and reference_answer:
            lines.append(f"   参考答案：{reference_answer}（仅用于讲解，不要直接展示给学生）")
        last_attempt_at = item.get("last_attempt_at")
        if isinstance(last_attempt_at, str) and last_attempt_at:
            lines.append(f"   上次作答：{last_attempt_at}")
    return "\n".join(lines)


def make_question_bank_tools() -> list[BaseTool]:
    @tool(args_schema=SearchQuestionsInput, description=_SEARCH_DESCRIPTION)
    def search_questions(
        *,
        scope: QuestionScope = "all",
        query: str | None = None,
        question_type: QuestionType | None = None,
        knowledge_point_id: str | None = None,
        knowledge_point_prefix: str | None = None,
        limit: int = 10,
        offset: int = 0,
        detail: QuestionDetail = "summary",
        runtime: ToolRuntime,
    ) -> str:
        search_input = SearchQuestionsInput(
            scope=scope,
            query=query,
            question_type=question_type,
            knowledge_point_id=knowledge_point_id,
            knowledge_point_prefix=knowledge_point_prefix,
            limit=limit,
            offset=offset,
            detail=detail,
        )
        try:
            user_id = user_id_from_config(runtime.config)
            payload = search_questions_api(user_id, search_input)
        except QuestionBankApiError as e:
            return f"题库检索失败：{e}"
        except Exception as e:  # 不让基础设施错误打断教学
            return f"题库检索失败（{type(e).__name__}）"
        return _format_search(payload)

    @tool(args_schema=SaveQuestionInput, description=_SAVE_DESCRIPTION)
    def save_question(
        *,
        question_type: QuestionType,
        stem: str,
        options: list[str] | None = None,
        correct_option: str | None = None,
        reference_answer: str | None = None,
        primary_knowledge_point_id: str,
        secondary_knowledge_point_ids: list[str] | None = None,
        runtime: ToolRuntime,
    ) -> str:
        save_input = SaveQuestionInput(
            question_type=question_type,
            stem=stem,
            options=options,
            correct_option=correct_option,
            reference_answer=reference_answer,
            primary_knowledge_point_id=primary_knowledge_point_id,
            secondary_knowledge_point_ids=secondary_knowledge_point_ids or [],
        )
        try:
            user_id = user_id_from_config(runtime.config)
            payload = save_question_api(user_id, save_input)
        except QuestionBankApiError as e:
            return f"题目保存失败：{e}"
        except Exception as e:  # 不让基础设施错误打断教学
            return f"题目保存失败（{type(e).__name__}）"
        question_id = payload.get("question_id")
        if not isinstance(question_id, str) or not question_id:
            return "题目保存失败：题库服务未返回题目 ID。"
        return f"已保存到我的题库（question_id={question_id}，不要展示给学生）。"

    return [search_questions, save_question]
