import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest
from deepagents import FilesystemPermission
from deepagents.backends import CompositeBackend, StoreBackend
from deepagents.middleware.filesystem import (
    FilesystemMiddleware,
    FilesystemOperation,
    _check_fs_permission,
)
from deepagents.middleware.skills import _list_skills
from langchain_core.callbacks import BaseCallbackHandler
from langchain_deepseek import ChatDeepSeek

from agent import main
from agent.core.constants import RESOURCE_DIR
from agent.main import build_exp_agent, build_teach_agent
from agent.runtime.utils import load_prompt

APP_DIR = Path(__file__).resolve().parents[1]


class _GraphNode(Protocol):
    bound: object


class _Graph(Protocol):
    nodes: Mapping[str, _GraphNode]


class _ToolNode(Protocol):
    tools_by_name: Mapping[str, object]


def _fake_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-flash",
        api_key="test",
        base_url="http://127.0.0.1:1",
    )


def _build_exp_graph(monkeypatch: pytest.MonkeyPatch) -> _Graph:
    monkeypatch.setattr(main, "get_llm", _fake_llm)
    monkeypatch.setattr(main, "get_langfuse_handler", lambda: BaseCallbackHandler())
    return cast(_Graph, build_exp_agent({}))


def _build_teach_graph(monkeypatch: pytest.MonkeyPatch) -> _Graph:
    monkeypatch.setattr(main, "get_llm", _fake_llm)
    monkeypatch.setattr(main, "get_langfuse_handler", lambda: BaseCallbackHandler())
    return cast(_Graph, build_teach_agent({}))


def _tool_names(graph: _Graph) -> set[str]:
    bound = cast(_ToolNode, graph.nodes["tools"].bound)
    return set(bound.tools_by_name)


def _capture_agent_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, dict[str, object]]:
    calls: dict[str, dict[str, object]] = {}

    class _FakeGraph:
        def with_config(self, config: Mapping[str, object]) -> _FakeGraph:
            return self

    def fake_create_agent(**kwargs: object) -> _FakeGraph:
        calls[str(kwargs["name"])] = kwargs
        return _FakeGraph()

    monkeypatch.setattr(main, "create_deep_agent", fake_create_agent)
    monkeypatch.setattr(main, "get_llm", _fake_llm)
    monkeypatch.setattr(main, "get_langfuse_handler", lambda: BaseCallbackHandler())

    build_exp_agent({})
    build_teach_agent({})
    return calls


def test_base_prompt_is_agent_neutral() -> None:
    text = load_prompt("base")

    assert "计算机网络课程智能体" in text
    assert "memory-maintenance" in text
    assert "execute" not in text
    assert "AGS" not in text
    assert "沙箱" not in text
    assert "/skills/lab/" not in text
    assert "traceroute" not in text
    assert "ask_student" not in text


def test_lab_prompt_keeps_sandbox_and_experiment_skill() -> None:
    text = load_prompt("base", "lab")

    assert "沙箱" in text
    assert "execute" in text
    assert "/skills/lab/traceroute-lab/SKILL.md" in text
    assert "普通文本" in text
    assert "ask_student" not in text


def test_image_prompt_is_shared_by_both_agents() -> None:
    base = load_prompt("base")

    assert "[图片]" in base
    assert "view_image" not in base
    assert "实验截图" in load_prompt("base", "lab")


def test_blobs_route_keeps_payloads_out_of_checkpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture_agent_kwargs(monkeypatch)

    for kwargs in calls.values():
        backend = cast(CompositeBackend, kwargs["backend"])
        assert isinstance(backend.routes["/blobs/"], StoreBackend)


def test_agents_offload_message_images(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _capture_agent_kwargs(monkeypatch)

    assert set(calls) == {"exp_agent", "teach_agent"}
    for kwargs in calls.values():
        middleware = cast(list[object], kwargs["middleware"])
        [filesystem] = [
            item for item in middleware if isinstance(item, FilesystemMiddleware)
        ]
        assert filesystem._offload_binary_content is True


def test_prompts_do_not_leak_implementation_details() -> None:
    texts = {
        name: load_prompt("base", name) for name in ("lab", "teaching")
    }

    for name, text in texts.items():
        assert "backend" not in text, name
        assert "StateBackend" not in text, name
        assert "teach_agent" not in text, name
        assert "exp_agent" not in text, name
        assert "owner_id" not in text, name


def test_experiment_resources_do_not_reference_ask_student() -> None:
    paths = [
        RESOURCE_DIR / "prompt" / "base.md",
        RESOURCE_DIR / "prompt" / "lab.md",
        RESOURCE_DIR / "skills" / "lab" / "traceroute-lab" / "SKILL.md",
    ]
    for path in paths:
        assert "ask_student" not in path.read_text(encoding="utf-8")


def test_skill_discovery_matches_agent_tracks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture_agent_kwargs(monkeypatch)
    exp_backend = cast(CompositeBackend, calls["exp_agent"]["backend"])
    teach_backend = cast(CompositeBackend, calls["teach_agent"]["backend"])

    exp_skills = {
        skill["name"]
        for source in ["/skills/common/", "/skills/lab/"]
        for skill in _list_skills(exp_backend, source)
    }
    teach_skills = {
        skill["name"]
        for source in ["/skills/common/", "/skills/teaching/"]
        for skill in _list_skills(teach_backend, source)
    }

    assert exp_skills == {"diagrams", "memory-maintenance", "traceroute-lab"}
    assert teach_skills == {
        "ask-question",
        "computer-networks-textbook",
        "diagrams",
        "memory-maintenance",
    }


def test_teach_memory_permissions(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = _capture_agent_kwargs(monkeypatch)["teach_agent"]
    rules = cast(list[FilesystemPermission], kwargs["permissions"])
    operation: FilesystemOperation = "write"

    assert _check_fs_permission(rules, operation, "/memory/teaching/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/profile.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/lab/AGENTS.md") == "deny"
    assert _check_fs_permission(rules, operation, "/skills/teaching/ask-question/SKILL.md") == "deny"
    assert _check_fs_permission(rules, operation, "/root/workspace/traceroute.py") == "deny"


def test_exp_memory_permissions(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = _capture_agent_kwargs(monkeypatch)["exp_agent"]
    rules = cast(list[FilesystemPermission], kwargs["permissions"])
    operation: FilesystemOperation = "write"

    assert _check_fs_permission(rules, operation, "/memory/lab/learning.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/profile.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/teaching/AGENTS.md") == "deny"
    assert _check_fs_permission(rules, operation, "/skills/teaching/ask-question/SKILL.md") == "deny"
    assert _check_fs_permission(rules, operation, "/root/workspace/traceroute.py") == "allow"


def test_teach_graph_uses_default_and_question_bank_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools = _tool_names(_build_teach_graph(monkeypatch))

    assert "ask_student" in tools
    assert "search_questions" in tools
    assert "save_question" in tools
    assert "read_file" in tools
    assert "write_file" in tools
    assert "delete" in tools
    assert "execute" in tools
    assert "task" in tools


def test_exp_graph_has_no_ask_student(monkeypatch: pytest.MonkeyPatch) -> None:
    tools = _tool_names(_build_exp_graph(monkeypatch))

    assert "ask_student" not in tools
    assert "read_file" in tools
    assert "execute" in tools
    assert "task" in tools


def test_both_graphs_mount_session_title_middleware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exp = _build_exp_graph(monkeypatch)
    teach = _build_teach_graph(monkeypatch)

    assert "session_title.after_agent" in exp.nodes
    assert "session_title.after_agent" in teach.nodes


def test_prompt_and_skill_layout() -> None:
    assert (RESOURCE_DIR / "prompt" / "base.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "lab.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "teaching.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "title.md").is_file()
    assert not (RESOURCE_DIR / "prompt" / "system.md").exists()

    assert (RESOURCE_DIR / "skills" / "teaching" / "ask-question" / "SKILL.md").is_file()
    assert (RESOURCE_DIR / "skills" / "teaching" / "ask-question" / "bank.md").is_file()
    assert (RESOURCE_DIR / "skills" / "common" / "diagrams" / "SKILL.md").is_file()
    assert (RESOURCE_DIR / "skills" / "common" / "memory-maintenance" / "SKILL.md").is_file()
    assert (RESOURCE_DIR / "skills" / "lab" / "traceroute-lab" / "SKILL.md").is_file()
    assert (
        RESOURCE_DIR / "skills" / "lab" / "traceroute-lab" / "chapters" / "01-认识-traceroute.md"
    ).is_file()
    assert (
        RESOURCE_DIR / "skills" / "teaching" / "computer-networks-textbook" / "SKILL.md"
    ).is_file()
    assert (
        RESOURCE_DIR
        / "skills"
        / "teaching"
        / "computer-networks-textbook"
        / "textbook"
        / "00-toc.md"
    ).is_file()
    assert not (RESOURCE_DIR / "materials").exists()
    assert not (RESOURCE_DIR / "skills" / "common" / "ask-question").exists()
    assert not (RESOURCE_DIR / "skills" / "ask-question").exists()
    assert not (RESOURCE_DIR / "skills" / "memory-maintenance").exists()
    assert not (RESOURCE_DIR / "skills" / "traceroute-lab").exists()
    # 旧名字不能复活
    assert not (RESOURCE_DIR / "skills" / "teaching" / "ask-student").exists()
    assert not (RESOURCE_DIR / "skills" / "teaching" / "question-bank").exists()
    assert not (RESOURCE_DIR / "skills" / "teaching" / "computer-networks").exists()


def test_langgraph_registers_both_agents() -> None:
    config = json.loads((APP_DIR / "langgraph.json").read_text())

    assert config["graphs"]["exp_agent"] == "./agent/main.py:build_exp_agent"
    assert config["graphs"]["teach_agent"] == "./agent/main.py:build_teach_agent"


def test_docker_image_serves_both_agents() -> None:
    dockerfile = (APP_DIR.parents[1] / "deploy" / "docker" / "agent.Dockerfile").read_text()

    assert '"exp_agent"' in dockerfile
    assert '"teach_agent"' in dockerfile
