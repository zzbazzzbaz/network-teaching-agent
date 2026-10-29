from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime

from agent.infra.question_bank_api import (
    QuestionBankError,
    SearchResponse,
)
from agent.infra.question_bank_api import (
    save_question as save_question_api,
)
from agent.infra.question_bank_api import (
    search_questions as search_questions_api,
)
from agent.runtime.context import tool_context
from agent.tools.schemas.question import Question, QuestionMode
from agent.tools.schemas.question_bank import (
    QuestionDetail,
    QuestionScope,
    SaveQuestionInput,
    SearchQuestionsInput,
)

_SEARCH_DESCRIPTION = (
    "检索课程公共题库和学生的私人题库，用于找同类题、引用原题或了解练习历史。"
    "摘要足以挑题；讲解需要时再取回参考答案，一次最多 3 条。"
)
_SAVE_DESCRIPTION = (
    "把学生明确要求保存的题目加入他的私人题库。"
    "只在学生说“记下来/加入题库”时调用；不发布公共题。"
)


def _format_search(payload: SearchResponse) -> str:
    if not payload.items:
        return "没有找到符合条件的题目。"

    lines = [f"共 {payload.total} 条，当前显示 {len(payload.items)} 条。"]
    for index, item in enumerate(payload.items, start=1):
        primary = item.primary_knowledge_point
        lines.append(
            f"{index}. [{item.origin}] {item.question_type} · {primary.id} {primary.title}"
        )
        if item.secondary_knowledge_points:
            labels = "、".join(
                f"{point.id} {point.title}"
                for point in item.secondary_knowledge_points
            )
            lines.append(f"   辅知识点：{labels}")
        if item.stem_preview:
            lines.append(f"   摘要：{item.stem_preview}")
        if item.stem:
            lines.append(f"   题干：{item.stem}")
        if item.options:
            lines.append("   选项：" + " | ".join(item.options))
        if item.correct_option:
            lines.append(f"   参考答案：{item.correct_option}（仅用于讲解，不要直接展示给学生）")
        if item.reference_answer:
            lines.append(f"   参考答案：{item.reference_answer}（仅用于讲解，不要直接展示给学生）")
        if item.last_attempt_at:
            lines.append(f"   上次作答：{item.last_attempt_at}")
    return "\n".join(lines)


def make_question_bank_tools() -> list[BaseTool]:
    @tool(args_schema=SearchQuestionsInput, description=_SEARCH_DESCRIPTION)
    def search_questions(
        *,
        scope: QuestionScope = "all",
        query: str | None = None,
        question_type: QuestionMode | None = None,
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
            payload = search_questions_api(tool_context(runtime), search_input)
        except QuestionBankError as e:
            return f"题库检索失败：{e}"
        return _format_search(payload)

    @tool(args_schema=SaveQuestionInput, description=_SAVE_DESCRIPTION)
    def save_question(*, question: Question, runtime: ToolRuntime) -> str:
        try:
            result = save_question_api(tool_context(runtime), question)
        except QuestionBankError as e:
            return f"题目保存失败：{e}"
        return "已保存到学生的私人题库。"

    return [search_questions, save_question]
