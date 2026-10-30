from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import interrupt
from pydantic import ValidationError

from agent.infra.question_bank_api import (
    QuestionBankError,
    SearchResponse,
    record_practice_attempt,
)
from agent.infra.question_bank_api import (
    QuestionDetail as QuestionDetailPayload,
)
from agent.infra.question_bank_api import (
    create_question as create_question_api,
)
from agent.infra.question_bank_api import (
    get_question as get_question_api,
)
from agent.infra.question_bank_api import (
    save_question as save_question_api,
)
from agent.infra.question_bank_api import (
    search_questions as search_questions_api,
)
from agent.runtime.context import tool_context
from agent.tools.schemas.ask_student import AskStudentResume
from agent.tools.schemas.question import AskQuestion, Question, QuestionMode
from agent.tools.schemas.question_bank import (
    GetQuestionInput,
    ImportQuestionsInput,
    ImportQuestionsResume,
    PracticeQuestionInput,
    QuestionDetail,
    QuestionScope,
    SaveQuestionInput,
    SearchQuestionsInput,
)

_SEARCH_DESCRIPTION = (
    "检索课程公共题库和学生的私人题库，用于找同类题、引用原题或了解练习历史。"
    "摘要足以挑题；讲解需要时再取回参考答案，一次最多 3 条。"
    "细节见 /skills/teaching/ask-question/bank.md。"
)
_SAVE_DESCRIPTION = (
    "把学生明确要求保存的题目加入他的私人题库。"
    "只在学生说“记下来/加入题库”时调用；不发布公共题。"
    "细节见 /skills/teaching/ask-question/bank.md。"
)
_GET_DESCRIPTION = (
    "按题目 ID 读取题库原题，包含题干、选项、答案和知识点。"
    "用于从题库开始学习或核对题目；答案仅供讲解，不要直接展示给学生。"
)
_PRACTICE_DESCRIPTION = (
    "让学生练一道题库里已有的题，并把本次作答记录下来。"
    "需要生成私有练习副本时由工具处理；不要向学生解释题库内部机制。一次只练一道。"
)
_IMPORT_DESCRIPTION = (
    "把从文本或图片解析出的题目交给学生确认后，保存到他的私人题库。"
    "只在学生明确要求导入/保存题目时调用；单次最多 5 道；不发布公共题；不去重。"
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


def _format_detail(detail: QuestionDetailPayload) -> str:
    lines = [
        f"题目 ID：{detail.question_id}",
        f"题型：{'单选' if detail.question_type == 'single_choice' else '简答'}",
        (
            "知识点："
            f"{detail.primary_knowledge_point.id} "
            f"{detail.primary_knowledge_point.title}"
        ),
        f"题干：{detail.stem}",
    ]
    if detail.secondary_knowledge_points:
        lines.append(
            "辅知识点："
            + "、".join(
                f"{point.id} {point.title}"
                for point in detail.secondary_knowledge_points
            )
        )
    if detail.options:
        lines.append(
            "选项："
            + " | ".join(
                f"{chr(ord('A') + index)}. {option}"
                for index, option in enumerate(detail.options)
            )
        )
    if detail.correct_option:
        lines.append(
            f"正确答案：{detail.correct_option}（仅用于讲解，不要直接展示给学生）"
        )
    if detail.reference_answer:
        lines.append(
            f"参考答案：{detail.reference_answer}（仅用于讲解，不要直接展示给学生）"
        )
    if detail.last_attempt_at:
        lines.append(f"上次作答：{detail.last_attempt_at}")
    return "\n".join(lines)


def _format_practice_result(
    answer: str,
    *,
    reference: str | None,
    warning: str | None = None,
) -> str:
    lines = [f"学生答案：{answer}"]
    if reference:
        lines.append(f"参考答案：{reference}")
    if warning:
        lines.append(f"（题库记录失败，不影响继续：{warning}）")
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
            save_question_api(tool_context(runtime), question)
        except QuestionBankError as e:
            return f"题目保存失败：{e}"
        return "已保存到学生的私人题库。"

    @tool(args_schema=GetQuestionInput, description=_GET_DESCRIPTION)
    def get_question(*, question_id: str, runtime: ToolRuntime) -> str:
        try:
            detail = get_question_api(tool_context(runtime), question_id)
        except QuestionBankError as e:
            return f"题目读取失败：{e}"
        return _format_detail(detail)

    @tool(args_schema=PracticeQuestionInput, description=_PRACTICE_DESCRIPTION)
    def practice_question(*, question_id: str, runtime: ToolRuntime) -> str:
        context = tool_context(runtime)
        try:
            detail = get_question_api(context, question_id)
        except QuestionBankError as e:
            return f"题目读取失败：{e}"

        try:
            question = AskQuestion(
                mode=detail.question_type,
                stem=detail.stem,
                options=detail.options,
                correct_option=detail.correct_option,
                reference_answer=detail.reference_answer,
                primary_knowledge_point_id=detail.primary_knowledge_point.id,
                secondary_knowledge_point_ids=[
                    point.id for point in detail.secondary_knowledge_points
                ],
            )
        except ValidationError as e:
            return f"题目数据不完整，暂时不能练习：{e}"

        answer = interrupt(
            question.to_payload(),
            response_schema=AskStudentResume,
        ).answer
        reference = question.correct_option or question.reference_answer

        target_question_id = question_id
        if detail.origin == "public":
            try:
                copy = create_question_api(
                    context,
                    Question(
                        mode=question.mode,
                        stem=question.stem,
                        options=question.options,
                        correct_option=question.correct_option,
                        reference_answer=question.reference_answer,
                        primary_knowledge_point_id=question.primary_knowledge_point_id,
                        secondary_knowledge_point_ids=question.secondary_knowledge_point_ids,
                    ),
                    import_key=f"practice:{context.tool_call_id}",
                )
            except QuestionBankError as e:
                return _format_practice_result(
                    answer,
                    reference=reference,
                    warning=str(e),
                )
            target_question_id = str(copy.question_id)

        try:
            record = record_practice_attempt(
                context,
                question_id=target_question_id,
                answer=answer,
            )
        except QuestionBankError as e:
            return _format_practice_result(
                answer,
                reference=reference,
                warning=str(e),
            )
        return _format_practice_result(
            answer,
            reference=record.reference.reference_answer
            or record.reference.correct_option,
        )

    @tool(args_schema=ImportQuestionsInput, description=_IMPORT_DESCRIPTION)
    def import_questions(
        *,
        questions: list[Question],
        runtime: ToolRuntime,
    ) -> str:
        context = tool_context(runtime)
        resume = interrupt(
            {
                "type": "question_import",
                "questions": [
                    question.model_dump(mode="json") for question in questions
                ],
            },
            response_schema=ImportQuestionsResume,
        )
        if resume.action == "cancel":
            return "用户取消了导入，没有保存。"

        saved: list[str] = []
        failed: list[str] = []
        for index, question in enumerate(resume.questions):
            try:
                result = create_question_api(
                    context,
                    question,
                    import_key=f"{context.tool_call_id}:{index}",
                )
            except QuestionBankError as e:
                failed.append(f"第 {index + 1} 道：{e}")
            else:
                saved.append(str(result.question_id))

        if not saved:
            return "没有保存成功：" + "；".join(failed)

        lines = [f"已保存 {len(saved)} 道题到你的私人题库。"]
        if failed:
            lines.append("失败：")
            lines.extend(failed)
        return "\n".join(lines)

    return [
        search_questions,
        save_question,
        get_question,
        practice_question,
        import_questions,
    ]
