import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Literal, Protocol, cast

import pytest
from pydantic import ValidationError

import agent.infra.question_bank_api as question_bank_api_module
import agent.tools.question_bank as question_bank_module
from agent.infra.question_bank_api import (
    KnowledgePointRef,
    PracticeAttemptResponse,
    QuestionBankError,
    QuestionReference,
    SaveQuestionResponse,
    SearchItem,
    SearchResponse,
)
from agent.infra.question_bank_api import (
    QuestionDetail as QuestionDetailPayload,
)
from agent.runtime.context import ToolContext
from agent.tools.question_bank import make_question_bank_tools
from agent.tools.schemas.question import Question
from agent.tools.schemas.question_bank import (
    GetQuestionInput,
    ImportQuestionsResume,
    PracticeQuestionInput,
    SearchQuestionsInput,
)


class _ToolWithFunc(Protocol):
    func: Callable[..., str]


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        config={
            "configurable": {
                "langgraph_auth_user_id": "user-1",
                "thread_id": "thread-1",
            }
        },
        tool_call_id="call-1",
    )


def _tools() -> dict[str, _ToolWithFunc]:
    return {
        tool.name: cast(_ToolWithFunc, tool)
        for tool in make_question_bank_tools()
    }


def test_search_questions_formats_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    question_id = uuid.uuid4()

    def fake_search(context: ToolContext, query: SearchQuestionsInput) -> SearchResponse:
        captured["context"] = context
        captured["query"] = query
        return SearchResponse(
            items=[
                SearchItem(
                    question_id=question_id,
                    origin="mine",
                    question_type="single_choice",
                    stem_preview="TCP 慢开始阶段 cwnd 如何变化？",
                    primary_knowledge_point=KnowledgePointRef(
                        id="5.8.2",
                        title="TCP的拥塞控制方法",
                    ),
                    secondary_knowledge_points=[],
                    last_attempt_at="2026-10-28T10:00:00Z",
                )
            ],
            total=1,
            limit=10,
            offset=0,
        )

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    result = _tools()["search_questions"].func(
        scope="mine",
        knowledge_point_id="5.8.2",
        runtime=_runtime(),
    )

    assert "共 1 条" in result
    assert "[mine] single_choice · 5.8.2 TCP的拥塞控制方法" in result
    assert f"题目 ID（内部使用，不要展示给学生）：{question_id}" in result
    assert "上次作答：2026-10-28T10:00:00Z" in result
    context = captured["context"]
    assert isinstance(context, ToolContext)
    assert context.user_id == "user-1"
    query_value = captured["query"]
    assert isinstance(query_value, SearchQuestionsInput)
    assert query_value.scope == "mine"


def test_search_questions_returns_error_without_fabricating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search(context: ToolContext, query: SearchQuestionsInput) -> SearchResponse:
        raise QuestionBankError("题库服务不可用")

    monkeypatch.setattr(question_bank_module, "search_questions_api", fake_search)
    result = _tools()["search_questions"].func(runtime=_runtime())

    assert "题库检索失败" in result
    assert "TCP" not in result


def test_search_questions_requires_auth() -> None:
    runtime = SimpleNamespace(config={"configurable": {}}, tool_call_id="call-1")

    with pytest.raises(KeyError):
        _tools()["search_questions"].func(runtime=runtime)


def test_save_question(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    question_id = uuid.uuid4()

    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        captured["context"] = context
        captured["question"] = question
        return SaveQuestionResponse(question_id=question_id)

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)
    question = Question(
        mode="short_answer",
        stem="为什么？",
        reference_answer="因为要匹配原始探测包",
        primary_knowledge_point_id="4.4.1",
    )

    result = _tools()["save_question"].func(question=question, runtime=_runtime())

    assert "已保存到学生的私人题库" in result
    assert f"题目 ID（内部使用，不要展示给学生）：{question_id}" in result
    context = captured["context"]
    assert isinstance(context, ToolContext)
    assert context.user_id == "user-1"
    assert captured["question"] is question


def test_save_question_sends_plain_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        captured["question"] = question
        return SaveQuestionResponse(question_id=uuid.uuid4())

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)
    question = Question(
        mode="single_choice",
        stem="选一个",
        options=["直接转发", "回 ICMP Time Exceeded"],
        correct_option="B",
        primary_knowledge_point_id="4.2.5",
    )

    _tools()["save_question"].func(question=question, runtime=_runtime())

    saved = captured["question"]
    assert isinstance(saved, Question)
    assert saved.options == ["直接转发", "回 ICMP Time Exceeded"]


def test_save_question_returns_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_save(context: ToolContext, question: Question) -> SaveQuestionResponse:
        raise QuestionBankError("题库服务返回 422：options: 选项内容不能为空")

    monkeypatch.setattr(question_bank_module, "save_question_api", fake_save)

    result = _tools()["save_question"].func(
        question=Question(
            mode="short_answer",
            stem="为什么？",
            primary_knowledge_point_id="4.4.1",
        ),
        runtime=_runtime(),
    )

    assert "题目保存失败" in result
    assert "选项内容不能为空" in result


def _detail(
    *,
    origin: Literal["public", "mine"] = "mine",
    question_type: Literal["single_choice", "short_answer"] = "single_choice",
    **overrides: object,
) -> QuestionDetailPayload:
    data: dict[str, object] = {
        "question_id": uuid.uuid4(),
        "origin": origin,
        "question_type": question_type,
        "stem": "TTL=1 时第一台路由器会做什么？",
        "options": ["直接转发", "回 ICMP Time Exceeded"],
        "correct_option": "B",
        "reference_answer": None,
        "primary_knowledge_point": KnowledgePointRef(
            id="4.2.5",
            title="IPv4 数据报的发送和转发过程",
        ),
        "secondary_knowledge_points": [],
        "last_attempt_at": None,
    }
    data.update(overrides)
    return QuestionDetailPayload(**data)


def test_get_question_formats_detail_and_warns_about_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail()
    expected_question_id = uuid.uuid4()

    def fake_get(
        context: ToolContext,
        question_id: uuid.UUID,
    ) -> QuestionDetailPayload:
        assert context.user_id == "user-1"
        assert question_id == expected_question_id
        return detail

    monkeypatch.setattr(question_bank_module, "get_question_api", fake_get)
    result = _tools()["get_question"].func(
        question_id=expected_question_id,
        runtime=_runtime(),
    )

    assert "题目 ID：" in result
    assert "题干：TTL=1" in result
    assert "正确答案：B（仅用于讲解" in result
    assert "4.2.5" in result


def test_practice_question_records_attempt_on_private_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = _detail()
    question_id = uuid.uuid4()
    captured: dict[str, object] = {}

    def fake_get(
        context: ToolContext,
        question_id: uuid.UUID,
    ) -> QuestionDetailPayload:
        return detail

    def fake_interrupt(payload: object, *, response_schema: object) -> SimpleNamespace:
        captured["payload"] = payload
        return SimpleNamespace(answer="B")

    def fake_record(
        context: ToolContext,
        *,
        question_id: uuid.UUID,
        answer: str,
    ) -> PracticeAttemptResponse:
        captured["question_id"] = question_id
        captured["answer"] = answer
        return PracticeAttemptResponse(
            attempt_id=uuid.uuid4(),
            question_id=detail.question_id,
            reference=QuestionReference(correct_option="B"),
        )

    monkeypatch.setattr(question_bank_module, "get_question_api", fake_get)
    monkeypatch.setattr(question_bank_module, "interrupt", fake_interrupt)
    monkeypatch.setattr(question_bank_module, "record_practice_attempt", fake_record)

    result, artifact = _tools()["practice_question"].func(
        question_id=question_id,
        runtime=_runtime(),
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["type"] == "ask_student"
    assert captured["question_id"] == question_id
    assert captured["answer"] == "B"
    assert "学生答案：B" in result
    assert "参考答案：B" in result
    assert artifact["type"] == "practice_question"
    assert artifact["question"]["stem"] == detail.stem
    assert artifact["student_answer"] == "B"
    assert artifact["reference"] == "B"


def test_practice_question_public_creates_private_copy_and_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_id = uuid.uuid4()
    copy_id = uuid.uuid4()
    detail = _detail(origin="public", question_id=public_id)
    captured: dict[str, object] = {}

    def fake_get(
        context: ToolContext,
        question_id: uuid.UUID,
    ) -> QuestionDetailPayload:
        captured["read"] = question_id
        return detail

    def fake_interrupt(payload: object, *, response_schema: object) -> SimpleNamespace:
        captured["payload"] = payload
        return SimpleNamespace(answer="B")

    def fake_create(
        context: ToolContext,
        item: Question,
        *,
        import_key: str | None = None,
    ) -> SaveQuestionResponse:
        captured["copy"] = item
        captured["import_key"] = import_key
        return SaveQuestionResponse(question_id=copy_id)

    def fake_record(
        context: ToolContext,
        *,
        question_id: str,
        answer: str,
    ) -> PracticeAttemptResponse:
        captured["target"] = question_id
        captured["answer"] = answer
        return PracticeAttemptResponse(
            attempt_id=uuid.uuid4(),
            question_id=copy_id,
            reference=QuestionReference(correct_option="B"),
        )

    monkeypatch.setattr(question_bank_module, "get_question_api", fake_get)
    monkeypatch.setattr(question_bank_module, "interrupt", fake_interrupt)
    monkeypatch.setattr(question_bank_module, "create_question_api", fake_create)
    monkeypatch.setattr(question_bank_module, "record_practice_attempt", fake_record)

    result, artifact = _tools()["practice_question"].func(
        question_id=public_id,
        runtime=_runtime(),
    )

    assert captured["read"] == public_id
    copy = captured["copy"]
    assert isinstance(copy, Question)
    assert copy.mode == "single_choice"
    assert copy.stem == detail.stem
    assert captured["import_key"] == "practice:call-1"
    assert captured["target"] == str(copy_id)
    assert captured["answer"] == "B"
    assert "学生答案：B" in result
    assert "参考答案：B" in result
    assert "公共" not in result
    assert artifact["type"] == "practice_question"
    assert artifact["student_answer"] == "B"
    assert artifact["reference"] == "B"


def test_import_questions_saves_after_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    saved_id = uuid.uuid4()
    question = Question(
        mode="short_answer",
        stem="为什么？",
        reference_answer="因为要匹配原始探测包",
        primary_knowledge_point_id="4.4.1",
    )

    def fake_interrupt(payload: object, *, response_schema: object) -> ImportQuestionsResume:
        captured["payload"] = payload
        return ImportQuestionsResume(action="save", questions=[question])

    def fake_create(
        context: ToolContext,
        item: Question,
        *,
        import_key: str | None = None,
    ) -> SaveQuestionResponse:
        captured["import_key"] = import_key
        return SaveQuestionResponse(question_id=saved_id)

    monkeypatch.setattr(question_bank_module, "interrupt", fake_interrupt)
    monkeypatch.setattr(question_bank_module, "create_question_api", fake_create)

    result = _tools()["import_questions"].func(
        questions=[question],
        runtime=_runtime(),
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["type"] == "question_import"
    assert captured["import_key"] == "call-1:0"
    assert "已保存 1 道题" in result
    assert f"第 1 道：{saved_id}" in result


def test_import_questions_cancel_does_not_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_interrupt(payload: object, *, response_schema: object) -> ImportQuestionsResume:
        return ImportQuestionsResume(action="cancel")

    def fake_create(
        context: ToolContext,
        item: Question,
        *,
        import_key: str | None = None,
    ) -> SaveQuestionResponse:
        nonlocal called
        called = True
        return SaveQuestionResponse(question_id=uuid.uuid4())

    monkeypatch.setattr(question_bank_module, "interrupt", fake_interrupt)
    monkeypatch.setattr(question_bank_module, "create_question_api", fake_create)

    result = _tools()["import_questions"].func(
        questions=[Question(mode="short_answer", stem="为什么？", primary_knowledge_point_id="4.4.1")],
        runtime=_runtime(),
    )

    assert "取消了导入" in result
    assert called is False


def test_import_resume_accepts_frontend_question_shape() -> None:
    resume = ImportQuestionsResume.model_validate(
        {
            "action": "save",
            "questions": [
                {
                    "mode": "single_choice",
                    "stem": "TCP 慢开始阶段，cwnd 如何变化？",
                    "options": ["指数增长", "线性增长"],
                    "correct_option": "A",
                    "reference_answer": None,
                    "primary_knowledge_point_id": "5.8.2",
                    "secondary_knowledge_point_ids": [],
                }
            ],
        }
    )

    assert resume.questions[0].mode == "single_choice"
    assert resume.questions[0].correct_option == "A"


def test_question_tool_inputs_require_uuid() -> None:
    with pytest.raises(ValidationError):
        GetQuestionInput(question_id="q-1")
    with pytest.raises(ValidationError):
        PracticeQuestionInput(question_id="../../sandbox/ensure")


def test_question_api_rejects_non_uuid_path(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_request(method: str, path: str, **kwargs: object) -> QuestionDetailPayload:
        nonlocal called
        called = True
        return _detail()

    monkeypatch.setattr(question_bank_api_module, "_request", fake_request)

    with pytest.raises(QuestionBankError, match="题目 ID 格式不正确"):
        question_bank_api_module.get_question(
            ToolContext(user_id="user-1", thread_id="thread-1", tool_call_id="call-1"),
            "../../sandbox/ensure?x=",
        )
    assert called is False


def test_question_api_normalizes_uuid_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    question_id = uuid.uuid4()

    def fake_request(method: str, path: str, **kwargs: object) -> QuestionDetailPayload:
        captured["path"] = path
        return _detail()

    monkeypatch.setattr(question_bank_api_module, "_request", fake_request)

    question_bank_api_module.get_question(
        ToolContext(user_id="user-1", thread_id="thread-1", tool_call_id="call-1"),
        str(question_id).upper(),
    )

    assert captured["path"] == f"/internal/question-bank/questions/{question_id}"
