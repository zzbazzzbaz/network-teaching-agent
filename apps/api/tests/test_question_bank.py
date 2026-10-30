from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.schemas.question_bank import QuestionInput
from app.core.exceptions import UnprocessableError
from app.core.knowledge_points import (
    KNOWLEDGE_POINTS_PATH,
    knowledge_point_parents,
)
from app.models.question import Question, QuestionAttempt
from app.models.session import ChatSession
from app.models.user import Users
from app.repositories.question_repository import question_repository
from app.services.question_bank_service import question_bank_service
from tests.conftest import INTERNAL_TOKEN

RECORD = "/internal/question-bank/ask-student/record"
QUESTIONS = "/internal/question-bank/questions"


def _headers(user: Users) -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": str(user.user_id),
    }


def _question_payload(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "question_type": "single_choice",
        "stem": "TTL=1 时第一台路由器会做什么？",
        "options": ["直接转发", "回 ICMP Time Exceeded"],
        "correct_option": "B",
        "reference_answer": None,
        "primary_knowledge_point_id": "4.2.5",
        "secondary_knowledge_point_ids": ["4.4.1"],
    }
    payload.update(overrides)
    return payload


def _record_payload(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "thread_id": "thread-1",
        "tool_call_id": f"call-{uuid.uuid4().hex}",
        "question": _question_payload(),
        "answer": "B",
    }
    payload.update(overrides)
    return payload


def _create_public(
    client: TestClient,
    payload: dict[str, Any] | None = None,
) -> uuid.UUID:
    question_payload = QuestionInput.model_validate(payload or _question_payload())
    with cast(FastAPI, client.app).state.session_factory() as session:
        question = question_repository.create_question(
            session,
            owner_id=None,
            payload=question_payload,
        )
        session.commit()
        return question.question_id


def _create_private_attempt(
    client: TestClient,
    *,
    user_id: uuid.UUID,
    public_question_id: uuid.UUID,
) -> None:
    with cast(FastAPI, client.app).state.session_factory() as session:
        question_repository.create_attempt(
            session,
            user_id=user_id,
            question_id=public_question_id,
            thread_id="thread-1",
            tool_call_id=f"public-{uuid.uuid4().hex}",
            answer_text="B",
        )
        session.commit()


def test_internal_endpoints_require_token(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    assert client.post(RECORD, json=_record_payload()).status_code == 401
    assert (
        client.post(
            RECORD,
            json=_record_payload(),
            headers={
                "X-Internal-Token": "wrong",
                "X-User-Id": str(user.user_id),
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            RECORD,
            json=_record_payload(),
            headers={"X-Internal-Token": INTERNAL_TOKEN},
        ).status_code
        == 422
    )


def test_disabled_user_is_rejected(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user(status=False)
    response = client.post(RECORD, json=_record_payload(), headers=_headers(user))
    assert response.status_code == 403


def test_record_creates_private_question_and_attempt(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(RECORD, json=_record_payload(), headers=_headers(user))

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"question_id", "attempt_id", "reference"}
    assert body["reference"] == {"correct_option": "B", "reference_answer": None}
    assert "is_correct" not in body
    assert "result" not in body

    with cast(FastAPI, client.app).state.session_factory() as session:
        question = session.get(Question, uuid.UUID(body["question_id"]))
        attempt = session.get(QuestionAttempt, uuid.UUID(body["attempt_id"]))
        assert question is not None
        assert question.owner_id == user.user_id
        assert attempt is not None
        assert attempt.user_id == user.user_id
        assert attempt.answer_text == "B"
        assert attempt.note is None
        assert not hasattr(QuestionAttempt, "is_correct")


def test_record_short_answer_returns_reference(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        RECORD,
        json=_record_payload(
            question=_question_payload(
                question_type="short_answer",
                stem="为什么要匹配原始探测包？",
                options=None,
                correct_option=None,
                reference_answer="为了匹配原始探测包",
            ),
            answer="因为要匹配原始探测包",
        ),
        headers=_headers(user),
    )

    assert response.status_code == 200, response.text
    assert response.json()["reference"] == {
        "correct_option": None,
        "reference_answer": "为了匹配原始探测包",
    }


def test_record_is_idempotent_and_rejects_changed_payload(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    payload = _record_payload()
    first = client.post(RECORD, json=payload, headers=_headers(user))
    second = client.post(RECORD, json=payload, headers=_headers(user))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["attempt_id"] == second.json()["attempt_id"]

    changed = dict(payload)
    changed["answer"] = "A"
    conflict = client.post(RECORD, json=changed, headers=_headers(user))
    assert conflict.status_code == 409

    with cast(FastAPI, client.app).state.session_factory() as session:
        attempts = list(session.scalars(select(QuestionAttempt)))
        assert len(attempts) == 1


def test_record_does_not_deduplicate_questions(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    first = client.post(
        RECORD,
        json=_record_payload(tool_call_id="call-a"),
        headers=_headers(user),
    )
    second = client.post(
        RECORD,
        json=_record_payload(tool_call_id="call-b"),
        headers=_headers(user),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["question_id"] != second.json()["question_id"]

    with cast(FastAPI, client.app).state.session_factory() as session:
        assert len(list(session.scalars(select(Question)))) == 2


def test_record_accepts_non_letter_answer(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        RECORD,
        json=_record_payload(answer="不会"),
        headers=_headers(user),
    )
    assert response.status_code == 200, response.text

    with cast(FastAPI, client.app).state.session_factory() as session:
        attempt = session.scalar(select(QuestionAttempt))
        assert attempt is not None
        assert attempt.answer_text == "不会"


def test_record_rejects_invalid_knowledge_point(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        RECORD,
        json=_record_payload(
            question=_question_payload(primary_knowledge_point_id="9.9.9"),
        ),
        headers=_headers(user),
    )
    assert response.status_code == 422


def test_record_rejects_question_id(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        RECORD,
        json=_record_payload(question_id="public-question-id"),
        headers=_headers(user),
    )
    assert response.status_code == 422


def test_record_rejects_single_choice_reference_answer(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        RECORD,
        json=_record_payload(
            question=_question_payload(reference_answer="B 是对的"),
        ),
        headers=_headers(user),
    )
    assert response.status_code == 422


def test_create_private_question(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        QUESTIONS,
        json=_question_payload(),
        headers=_headers(user),
    )
    assert response.status_code == 201, response.text
    question_id = response.json()["question_id"]

    with cast(FastAPI, client.app).state.session_factory() as session:
        question = session.get(Question, uuid.UUID(question_id))
        assert question is not None
        assert question.owner_id == user.user_id


def test_private_question_keeps_plain_text_options(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    options = ["直接转发", "回 ICMP Time Exceeded"]
    response = client.post(
        QUESTIONS,
        json=_question_payload(options=options),
        headers=_headers(user),
    )
    assert response.status_code == 201, response.text

    with cast(FastAPI, client.app).state.session_factory() as session:
        question = session.get(Question, uuid.UUID(response.json()["question_id"]))
        assert question is not None
        assert question.options == options


def test_validation_error_detail_is_readable(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    response = client.post(
        QUESTIONS,
        json=_question_payload(options=["", "回 ICMP Time Exceeded"]),
        headers=_headers(user),
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert "选项内容不能为空" in detail


def test_search_scope_and_detail(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    public_id = _create_public(client)
    private = client.post(
        RECORD,
        json=_record_payload(
            question=_question_payload(
                stem="TCP 慢开始阶段 cwnd 如何变化？",
                primary_knowledge_point_id="5.8.2",
                secondary_knowledge_point_ids=[],
            )
        ),
        headers=_headers(user),
    )
    assert private.status_code == 200, private.text

    all_response = client.get(
        QUESTIONS,
        params={"scope": "all", "detail": "summary"},
        headers=_headers(user),
    )
    assert all_response.status_code == 200, all_response.text
    all_body = all_response.json()
    assert all_body["total"] == 2
    origins = {item["origin"] for item in all_body["items"]}
    assert origins == {"public", "mine"}

    public_response = client.get(
        QUESTIONS,
        params={"scope": "public"},
        headers=_headers(user),
    )
    assert public_response.json()["total"] == 1
    assert public_response.json()["items"][0]["question_id"] == str(public_id)

    mine_response = client.get(
        QUESTIONS,
        params={"scope": "mine", "knowledge_point_prefix": "5.8"},
        headers=_headers(user),
    )
    assert mine_response.status_code == 200, mine_response.text
    assert mine_response.json()["total"] == 1
    item = mine_response.json()["items"][0]
    assert item["last_attempt_at"] is not None
    assert "correct_option" not in item
    assert "reference_answer" not in item
    assert "note" not in item

    full_response = client.get(
        QUESTIONS,
        params={"scope": "mine", "detail": "full", "limit": 20},
        headers=_headers(user),
    )
    assert full_response.status_code == 200, full_response.text
    full_body = full_response.json()
    assert full_body["limit"] == 3
    assert full_body["items"][0]["correct_option"] == "B"
    assert full_body["items"][0]["stem"]


def test_search_summary_does_not_return_answers_for_public(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    _create_public(client)

    response = client.get(
        QUESTIONS,
        params={"scope": "public", "detail": "summary"},
        headers=_headers(user),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "correct_option" not in item
    assert "reference_answer" not in item


def test_replace_public_questions_keeps_private_data(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    old_public_id = _create_public(client)
    private = client.post(RECORD, json=_record_payload(), headers=_headers(user))
    private_question_id = private.json()["question_id"]

    with cast(FastAPI, client.app).state.session_factory() as session:
        deleted, inserted = question_bank_service.replace_public_questions(
            session,
            questions=[
                QuestionInput.model_validate(
                    _question_payload(
                        stem="新的公共题",
                        primary_knowledge_point_id="5.8.2",
                        secondary_knowledge_point_ids=[],
                    )
                )
            ],
            dry_run=False,
        )
        assert (deleted, inserted) == (1, 1)
        assert session.get(Question, old_public_id) is None
        assert session.get(Question, uuid.UUID(private_question_id)) is not None
        assert session.scalar(select(QuestionAttempt)) is not None


def test_public_seed_file_is_valid() -> None:
    from app.scripts.cli import _load_public_questions

    questions = _load_public_questions(
        Path(__file__).resolve().parents[1]
        / "app"
        / "data"
        / "question_bank"
        / "computer-networks-v1.json"
    )
    assert len(questions) == 24
    assert sum(question.question_type == "single_choice" for question in questions) == 12
    assert sum(question.question_type == "short_answer" for question in questions) == 12


def test_knowledge_points_match_textbook_toc() -> None:
    toc_path = (
        Path(__file__).resolve().parents[2]
        / "agent"
        / "agent"
        / "resources"
        / "skills"
        / "teaching"
        / "computer-networks-textbook"
        / "textbook"
        / "00-toc.md"
    )
    toc_ids: set[str] = set()
    for line in toc_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("- "):
            continue
        title = text[2:].strip().split("（教材", 1)[0].strip()
        if not title or title in {"本章的重要概念", "习题"} or title.startswith("附录"):
            continue
        chapter = re.match(r"^第(\d+)章\s+", title)
        if chapter:
            toc_ids.add(chapter.group(1))
            continue
        section = re.match(r"^(\d+(?:\.\d+)+)\s+", title)
        if section:
            toc_ids.add(section.group(1))
    toc_ids.add("99")

    payload = json.loads(KNOWLEDGE_POINTS_PATH.read_text(encoding="utf-8"))
    json_ids = {node["id"] for node in payload["nodes"]}
    assert json_ids == toc_ids


def test_replace_public_questions_aborts_on_public_attempt(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    public_id = _create_public(client)
    _create_private_attempt(client, user_id=user.user_id, public_question_id=public_id)

    with cast(FastAPI, client.app).state.session_factory() as session:
        try:
            question_bank_service.replace_public_questions(
                session,
                questions=[QuestionInput.model_validate(_question_payload())],
                dry_run=False,
            )
        except UnprocessableError as e:
            assert "公共题存在作答记录" in str(e)
        else:
            raise AssertionError("expected UnprocessableError")


PUBLIC_QUESTIONS = "/api/v1/question-bank/questions"
PUBLIC_KNOWLEDGE_POINTS = "/api/v1/question-bank/knowledge-points"
PUBLIC_KNOWLEDGE_POINT_COUNTS = (
    "/api/v1/question-bank/knowledge-points/counts"
)


def _login_headers(
    client: TestClient,
    username: str = "alice",
    password: str = "password123",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_public_question_routes_require_auth(client: TestClient) -> None:
    assert client.get(PUBLIC_QUESTIONS).status_code == 401
    assert client.get(PUBLIC_KNOWLEDGE_POINTS).status_code == 401
    assert client.get(PUBLIC_KNOWLEDGE_POINT_COUNTS).status_code == 401


def test_public_question_search_and_detail(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)
    public_id = _create_public(client)
    private = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(stem="我的私有题"),
        headers=headers,
    )
    assert private.status_code == 201, private.text
    private_id = private.json()["question_id"]

    public_list = client.get(
        PUBLIC_QUESTIONS,
        params={"scope": "public"},
        headers=headers,
    )
    assert public_list.status_code == 200, public_list.text
    public_body = public_list.json()
    assert public_body["total"] == 1
    item = public_body["items"][0]
    assert item["question_id"] == str(public_id)
    assert item["origin"] == "public"
    assert "stem" not in item
    assert "options" not in item
    assert "correct_option" not in item
    assert "reference_answer" not in item
    assert item["last_attempt_at"] is None

    mine_list = client.get(
        PUBLIC_QUESTIONS,
        params={"scope": "mine"},
        headers=headers,
    )
    assert mine_list.status_code == 200
    assert mine_list.json()["items"][0]["question_id"] == private_id

    all_list = client.get(
        PUBLIC_QUESTIONS,
        params={"scope": "all"},
        headers=headers,
    )
    assert all_list.status_code == 200
    assert all_list.json()["total"] == 2

    detail = client.get(f"{PUBLIC_QUESTIONS}/{public_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["origin"] == "public"
    assert detail_body["correct_option"] == "B"
    assert detail_body["reference_answer"] is None
    assert detail_body["stem"] == _question_payload()["stem"]


def test_public_knowledge_points(client: TestClient, create_user: Callable[..., Users]) -> None:
    create_user()
    headers = _login_headers(client)

    response = client.get(PUBLIC_KNOWLEDGE_POINTS, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["course"] == "computer-networks"
    assert any(node["id"] == "5.8.2" for node in body["nodes"])

    invalid_id = client.get(
        PUBLIC_QUESTIONS,
        params={"knowledge_point_id": "9.9.9"},
        headers=headers,
    )
    assert invalid_id.status_code == 422

    invalid_prefix = client.get(
        PUBLIC_QUESTIONS,
        params={"knowledge_point_prefix": "9.9"},
        headers=headers,
    )
    assert invalid_prefix.status_code == 422


def test_public_create_update_and_delete_private_question(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)

    created = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    question_id = created.json()["question_id"]

    with cast(FastAPI, client.app).state.session_factory() as session:
        question = session.get(Question, uuid.UUID(question_id))
        assert question is not None
        assert question.owner_id == user.user_id

    updated = client.put(
        f"{PUBLIC_QUESTIONS}/{question_id}",
        json=_question_payload(
            question_type="short_answer",
            stem="修改后的题干",
            options=None,
            correct_option=None,
            reference_answer="参考答案",
            primary_knowledge_point_id="5.8.3",
            secondary_knowledge_point_ids=["5.8.2"],
        ),
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    updated_body = updated.json()
    assert updated_body["question_id"] == question_id
    assert updated_body["question_type"] == "short_answer"
    assert updated_body["stem"] == "修改后的题干"
    assert updated_body["correct_option"] is None
    assert updated_body["reference_answer"] == "参考答案"

    deleted = client.delete(f"{PUBLIC_QUESTIONS}/{question_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"{PUBLIC_QUESTIONS}/{question_id}", headers=headers).status_code == 404


def test_public_question_cannot_be_modified(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)
    public_id = _create_public(client)

    update = client.put(
        f"{PUBLIC_QUESTIONS}/{public_id}",
        json=_question_payload(),
        headers=headers,
    )
    assert update.status_code == 403
    delete = client.delete(f"{PUBLIC_QUESTIONS}/{public_id}", headers=headers)
    assert delete.status_code == 403


def test_other_users_private_question_is_hidden(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login_headers(client, "alice", "password123")
    bob = _login_headers(client, "bob", "password456")

    created = client.post(PUBLIC_QUESTIONS, json=_question_payload(), headers=alice)
    assert created.status_code == 201, created.text
    question_id = created.json()["question_id"]

    assert client.get(f"{PUBLIC_QUESTIONS}/{question_id}", headers=bob).status_code == 404
    assert (
        client.put(
            f"{PUBLIC_QUESTIONS}/{question_id}",
            json=_question_payload(),
            headers=bob,
        ).status_code
        == 404
    )
    assert client.delete(f"{PUBLIC_QUESTIONS}/{question_id}", headers=bob).status_code == 404


def test_delete_private_question_with_attempt_soft_deletes(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)
    created = client.post(PUBLIC_QUESTIONS, json=_question_payload(), headers=headers)
    assert created.status_code == 201, created.text
    question_id = uuid.UUID(created.json()["question_id"])
    _create_private_attempt(client, user_id=user.user_id, public_question_id=question_id)

    response = client.delete(f"{PUBLIC_QUESTIONS}/{question_id}", headers=headers)
    assert response.status_code == 204

    assert client.get(f"{PUBLIC_QUESTIONS}/{question_id}", headers=headers).status_code == 404
    listed = client.get(
        PUBLIC_QUESTIONS,
        params={"scope": "mine"},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    with cast(FastAPI, client.app).state.session_factory() as session:
        question = session.get(Question, question_id)
        assert question is not None
        assert question.deleted_at is not None
        attempts = list(
            session.scalars(
                select(QuestionAttempt).where(
                    QuestionAttempt.question_id == question_id
                )
            )
        )
        assert len(attempts) == 1


def _create_private_question(
    client: TestClient,
    headers: dict[str, str],
    **overrides: object,
) -> uuid.UUID:
    response = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(**overrides),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["question_id"])


def _create_session(
    client: TestClient,
    user: Users,
    *,
    title: str = "第5章 运输层",
    agent_id: str = "teach_agent",
) -> uuid.UUID:
    with cast(FastAPI, client.app).state.session_factory() as session:
        chat_session = ChatSession(
            user_id=user.user_id,
            agent_id=agent_id,
            title=title,
            title_source="user",
        )
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session.session_id


def test_internal_get_question_is_scoped(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    alice = create_user("alice", "password123")
    bob = create_user("bob", "password456")
    alice_headers = _login_headers(client, "alice", "password123")
    bob_headers = _login_headers(client, "bob", "password456")

    private_id = _create_private_question(client, alice_headers)
    private = client.get(f"{QUESTIONS}/{private_id}", headers=_headers(alice))
    assert private.status_code == 200, private.text
    assert private.json()["origin"] == "mine"
    assert private.json()["correct_option"] == "B"

    assert client.get(f"{QUESTIONS}/{private_id}", headers=_headers(bob)).status_code == 404
    assert (
        client.get(f"{PUBLIC_QUESTIONS}/{private_id}", headers=bob_headers).status_code
        == 404
    )

    public_id = _create_public(client)
    public = client.get(f"{QUESTIONS}/{public_id}", headers=_headers(alice))
    assert public.status_code == 200, public.text
    assert public.json()["origin"] == "public"

    assert client.delete(f"{PUBLIC_QUESTIONS}/{private_id}", headers=alice_headers).status_code == 204
    assert client.get(f"{QUESTIONS}/{private_id}", headers=_headers(alice)).status_code == 404


def test_practice_attempt_records_on_existing_question(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)
    question_id = _create_private_question(client, headers)
    session_id = _create_session(client, user)
    payload = {
        "thread_id": str(session_id),
        "tool_call_id": f"practice-{uuid.uuid4().hex}",
        "answer": "B",
    }

    response = client.post(
        f"{QUESTIONS}/{question_id}/attempts",
        json=payload,
        headers=_headers(user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question_id"] == str(question_id)
    assert body["reference"] == {"correct_option": "B", "reference_answer": None}

    with cast(FastAPI, client.app).state.session_factory() as session:
        attempts = list(
            session.scalars(
                select(QuestionAttempt).where(
                    QuestionAttempt.question_id == question_id
                )
            )
        )
        assert len(attempts) == 1
        assert attempts[0].answer_text == "B"
        assert attempts[0].thread_id == str(session_id)

    replay = client.post(
        f"{QUESTIONS}/{question_id}/attempts",
        json=payload,
        headers=_headers(user),
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["attempt_id"] == body["attempt_id"]

    conflict = client.post(
        f"{QUESTIONS}/{question_id}/attempts",
        json={**payload, "answer": "A"},
        headers=_headers(user),
    )
    assert conflict.status_code == 409


def test_practice_attempt_rejects_public_and_other_users(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    alice = create_user("alice", "password123")
    bob = create_user("bob", "password456")
    alice_headers = _login_headers(client, "alice", "password123")

    public_id = _create_public(client)
    public = client.post(
        f"{QUESTIONS}/{public_id}/attempts",
        json={
            "tool_call_id": f"public-{uuid.uuid4().hex}",
            "answer": "B",
        },
        headers=_headers(alice),
    )
    assert public.status_code == 422

    private_id = _create_private_question(client, alice_headers)
    other = client.post(
        f"{QUESTIONS}/{private_id}/attempts",
        json={
            "tool_call_id": f"other-{uuid.uuid4().hex}",
            "answer": "B",
        },
        headers=_headers(bob),
    )
    assert other.status_code == 404


def test_question_attempt_history_returns_session_and_handles_deletion(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)
    question_id = _create_private_question(client, headers)
    session_id = _create_session(client, user, title="第5章 运输层")

    recorded = client.post(
        f"{QUESTIONS}/{question_id}/attempts",
        json={
            "thread_id": str(session_id),
            "tool_call_id": f"history-{uuid.uuid4().hex}",
            "answer": "B",
        },
        headers=_headers(user),
    )
    assert recorded.status_code == 200, recorded.text

    history = client.get(
        f"{PUBLIC_QUESTIONS}/{question_id}/attempts",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    body = history.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["answer_text"] == "B"
    assert item["thread_id"] == str(session_id)
    assert item["session_title"] == "第5章 运输层"
    assert item["agent_id"] == "teach_agent"
    assert item["session_exists"] is True
    assert "is_correct" not in item

    with cast(FastAPI, client.app).state.session_factory() as session:
        chat_session = session.get(ChatSession, session_id)
        assert chat_session is not None
        session.delete(chat_session)
        session.commit()

    deleted = client.get(
        f"{PUBLIC_QUESTIONS}/{question_id}/attempts",
        headers=headers,
    )
    assert deleted.status_code == 200
    deleted_item = deleted.json()["items"][0]
    assert deleted_item["session_exists"] is False
    assert deleted_item["session_title"] is None
    assert deleted_item["agent_id"] is None


def test_attempt_history_is_user_scoped(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice_headers = _login_headers(client, "alice", "password123")
    bob_headers = _login_headers(client, "bob", "password456")
    question_id = _create_private_question(client, alice_headers)

    assert (
        client.get(
            f"{PUBLIC_QUESTIONS}/{question_id}/attempts",
            headers=bob_headers,
        ).status_code
        == 404
    )

    public_id = _create_public(client)
    public_history = client.get(
        f"{PUBLIC_QUESTIONS}/{public_id}/attempts",
        headers=alice_headers,
    )
    assert public_history.status_code == 200
    assert public_history.json()["items"] == []


def test_internal_question_import_key_is_idempotent(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    payload = {**_question_payload(stem="导入的题"), "import_key": "call-1:0"}

    created = client.post(QUESTIONS, json=payload, headers=_headers(user))
    assert created.status_code == 201, created.text
    question_id = created.json()["question_id"]

    replay = client.post(QUESTIONS, json=payload, headers=_headers(user))
    assert replay.status_code == 201, replay.text
    assert replay.json()["question_id"] == question_id

    with cast(FastAPI, client.app).state.session_factory() as session:
        questions = list(
            session.scalars(select(Question).where(Question.owner_id == user.user_id))
        )
        assert len(questions) == 1
        assert questions[0].import_key == "call-1:0"

    conflict = client.post(
        QUESTIONS,
        json={**payload, "stem": "另一道题"},
        headers=_headers(user),
    )
    assert conflict.status_code == 409


def test_internal_question_import_key_can_be_reused_after_soft_delete(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)
    payload = {**_question_payload(stem="会被删除的导入题"), "import_key": "call-2:0"}

    created = client.post(
        QUESTIONS,
        json=payload,
        headers=_headers(user),
    )
    assert created.status_code == 201, created.text
    first_id = created.json()["question_id"]
    assert client.delete(f"{PUBLIC_QUESTIONS}/{first_id}", headers=headers).status_code == 204

    again = client.post(
        QUESTIONS,
        json=payload,
        headers=_headers(user),
    )
    assert again.status_code == 201, again.text
    assert again.json()["question_id"] != first_id


def test_public_create_rejects_import_key(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)
    response = client.post(
        PUBLIC_QUESTIONS,
        json={**_question_payload(), "import_key": "call-3:0"},
        headers=headers,
    )
    assert response.status_code == 422


def test_public_knowledge_point_counts_empty(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)
    body = _get_counts(client, headers)
    assert body["totals"] == {"all": 0, "public": 0, "mine": 0}
    assert body["counts"] == {"all": {}, "public": {}, "mine": {}}


def test_question_bank_openapi_includes_counts_and_match(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    assert PUBLIC_KNOWLEDGE_POINT_COUNTS in schema["paths"]
    parameters = schema["paths"][PUBLIC_QUESTIONS]["get"]["parameters"]
    assert any(
        parameter["name"] == "knowledge_point_match"
        for parameter in parameters
    )


def _get_counts(
    client: TestClient,
    headers: dict[str, str],
    **params: str | int,
) -> dict[str, Any]:
    response = client.get(
        PUBLIC_KNOWLEDGE_POINT_COUNTS,
        params=params,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_public_knowledge_point_counts_scope_and_rollup(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user("alice", "password123")
    create_user("bob", "password456")
    alice = _login_headers(client, "alice", "password123")
    bob = _login_headers(client, "bob", "password456")

    _create_public(
        client,
        _question_payload(
            primary_knowledge_point_id="5.8.2",
            secondary_knowledge_point_ids=["5.8.1"],
        ),
    )
    alice_private = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(
            stem="Alice 的私有题",
            primary_knowledge_point_id="5.8.3",
            secondary_knowledge_point_ids=["5.9.1"],
        ),
        headers=alice,
    )
    assert alice_private.status_code == 201, alice_private.text
    bob_private = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(
            stem="Bob 的私有题",
            primary_knowledge_point_id="5.8.2",
            secondary_knowledge_point_ids=[],
        ),
        headers=bob,
    )
    assert bob_private.status_code == 201, bob_private.text

    body = _get_counts(client, alice)
    assert body["totals"] == {"all": 2, "public": 1, "mine": 1}
    assert body["counts"]["public"]["5.8.2"] == 1
    assert body["counts"]["public"]["5.8"] == 1
    assert body["counts"]["public"]["5"] == 1
    assert "5.8.1" not in body["counts"]["public"]

    assert body["counts"]["all"]["5.8.2"] == 1
    assert body["counts"]["all"]["5.8.3"] == 1
    assert body["counts"]["all"]["5.8"] == 2
    assert body["counts"]["all"]["5"] == 2
    assert "5.8.1" not in body["counts"]["all"]
    assert "5.9.1" not in body["counts"]["all"]

    assert body["counts"]["mine"] == {
        "5.8.3": 1,
        "5.8": 1,
        "5": 1,
    }

    bob_body = _get_counts(client, bob)
    assert bob_body["totals"] == {"all": 2, "public": 1, "mine": 1}
    assert bob_body["counts"]["mine"]["5.8.2"] == 1
    assert bob_body["counts"]["mine"]["5.8"] == 1

    invalid = client.get(
        PUBLIC_QUESTIONS,
        params={"knowledge_point_prefix": "5.8", "knowledge_point_match": "bad"},
        headers=alice,
    )
    assert invalid.status_code == 422


def test_public_knowledge_point_counts_search_type_and_soft_delete(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)

    _create_public(
        client,
        _question_payload(
            stem="TCP 拥塞控制",
            primary_knowledge_point_id="5.8.2",
            secondary_knowledge_point_ids=[],
        ),
    )
    _create_public(
        client,
        _question_payload(
            stem="TCP 三次握手",
            question_type="short_answer",
            options=None,
            correct_option=None,
            reference_answer="SYN / SYN-ACK / ACK",
            primary_knowledge_point_id="5.8.3",
            secondary_knowledge_point_ids=[],
        ),
    )
    _create_public(
        client,
        _question_payload(
            stem="DNS 查询",
            primary_knowledge_point_id="4.2.5",
            secondary_knowledge_point_ids=[],
        ),
    )
    _create_public(
        client,
        _question_payload(
            stem="100% 命中",
            primary_knowledge_point_id="4.2.5",
            secondary_knowledge_point_ids=[],
        ),
    )
    _create_public(
        client,
        _question_payload(
            stem="1000 命中",
            primary_knowledge_point_id="4.2.5",
            secondary_knowledge_point_ids=[],
        ),
    )

    tcp = _get_counts(client, headers, query="TCP")
    assert tcp["totals"]["all"] == 2
    assert tcp["counts"]["all"]["5.8"] == 2
    assert "4.2.5" not in tcp["counts"]["all"]

    short = _get_counts(client, headers, question_type="short_answer")
    assert short["totals"]["all"] == 1
    assert short["counts"]["all"]["5.8.3"] == 1

    percent = _get_counts(client, headers, query="100%")
    assert percent["totals"]["all"] == 1
    assert percent["counts"]["all"]["4.2.5"] == 1

    created = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(
            stem="待删除的私有题",
            primary_knowledge_point_id="5.8.2",
            secondary_knowledge_point_ids=[],
        ),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    question_id = created.json()["question_id"]

    before = _get_counts(client, headers)
    assert before["totals"]["mine"] == 1
    assert before["counts"]["mine"]["5.8.2"] == 1

    deleted = client.delete(f"{PUBLIC_QUESTIONS}/{question_id}", headers=headers)
    assert deleted.status_code == 204

    after = _get_counts(client, headers)
    assert after["totals"]["mine"] == 0
    assert after["counts"]["mine"] == {}


def test_public_question_knowledge_point_match_primary(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    user = create_user()
    headers = _login_headers(client)
    _create_public(
        client,
        _question_payload(
            primary_knowledge_point_id="5.9.1",
            secondary_knowledge_point_ids=["5.8.2"],
        ),
    )

    any_prefix = client.get(
        PUBLIC_QUESTIONS,
        params={"knowledge_point_prefix": "5.8"},
        headers=headers,
    )
    assert any_prefix.status_code == 200, any_prefix.text
    assert any_prefix.json()["total"] == 1

    primary_prefix = client.get(
        PUBLIC_QUESTIONS,
        params={
            "knowledge_point_prefix": "5.8",
            "knowledge_point_match": "primary",
        },
        headers=headers,
    )
    assert primary_prefix.status_code == 200, primary_prefix.text
    assert primary_prefix.json()["total"] == 0

    primary_own_prefix = client.get(
        PUBLIC_QUESTIONS,
        params={
            "knowledge_point_prefix": "5.9",
            "knowledge_point_match": "primary",
        },
        headers=headers,
    )
    assert primary_own_prefix.status_code == 200, primary_own_prefix.text
    assert primary_own_prefix.json()["total"] == 1

    any_exact = client.get(
        PUBLIC_QUESTIONS,
        params={"knowledge_point_id": "5.8.2"},
        headers=headers,
    )
    assert any_exact.status_code == 200, any_exact.text
    assert any_exact.json()["total"] == 1

    primary_exact = client.get(
        PUBLIC_QUESTIONS,
        params={
            "knowledge_point_id": "5.8.2",
            "knowledge_point_match": "primary",
        },
        headers=headers,
    )
    assert primary_exact.status_code == 200, primary_exact.text
    assert primary_exact.json()["total"] == 0

    internal_any = client.get(
        QUESTIONS,
        params={"knowledge_point_prefix": "5.8"},
        headers=_headers(user),
    )
    assert internal_any.status_code == 200, internal_any.text
    assert internal_any.json()["total"] == 1

    internal_primary = client.get(
        QUESTIONS,
        params={
            "knowledge_point_prefix": "5.8",
            "knowledge_point_match": "primary",
        },
        headers=_headers(user),
    )
    assert internal_primary.status_code == 200, internal_primary.text
    assert internal_primary.json()["total"] == 0


def test_public_knowledge_point_counts_match_list_totals(
    client: TestClient,
    create_user: Callable[..., Users],
) -> None:
    create_user()
    headers = _login_headers(client)

    _create_public(
        client,
        _question_payload(
            primary_knowledge_point_id="5.8.2",
            secondary_knowledge_point_ids=["5.8.1"],
        ),
    )
    _create_public(
        client,
        _question_payload(
            stem="另一道公共题",
            primary_knowledge_point_id="4.2.5",
            secondary_knowledge_point_ids=[],
        ),
    )
    created = client.post(
        PUBLIC_QUESTIONS,
        json=_question_payload(
            stem="用于口径校验的私有题",
            primary_knowledge_point_id="5.8.3",
            secondary_knowledge_point_ids=["5.9.1"],
        ),
        headers=headers,
    )
    assert created.status_code == 201, created.text

    body = _get_counts(client, headers)
    for scope in ("all", "public", "mine"):
        counts = cast(dict[str, int], body["counts"][scope])
        for knowledge_point_id, count in counts.items():
            listed = client.get(
                PUBLIC_QUESTIONS,
                params={
                    "scope": scope,
                    "knowledge_point_prefix": knowledge_point_id,
                    "knowledge_point_match": "primary",
                    "limit": 1,
                },
                headers=headers,
            )
            assert listed.status_code == 200, listed.text
            assert listed.json()["total"] == count

    parents = knowledge_point_parents()
    roots = [node_id for node_id, parent_id in parents.items() if parent_id is None]
    for scope in ("all", "public", "mine"):
        root_sum = sum(
            cast(dict[str, int], body["counts"][scope]).get(root_id, 0)
            for root_id in roots
        )
        assert root_sum == body["totals"][scope]

    all_counts = cast(dict[str, int], body["counts"]["all"])
    public_counts = cast(dict[str, int], body["counts"]["public"])
    mine_counts = cast(dict[str, int], body["counts"]["mine"])
    for knowledge_point_id in set(all_counts) | set(public_counts) | set(mine_counts):
        assert all_counts.get(knowledge_point_id, 0) == (
            public_counts.get(knowledge_point_id, 0)
            + mine_counts.get(knowledge_point_id, 0)
        )
