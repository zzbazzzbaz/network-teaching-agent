import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest
from deepagents.middleware.filesystem import FilesystemOperation, _check_fs_permission
from deepagents.middleware.skills import _list_skills
from langchain_core.callbacks import BaseCallbackHandler
from langchain_deepseek import ChatDeepSeek

from agent import main
from agent.main import build_exp_agent, build_teach_agent
from agent.runtime.backends import build_exp_backend, build_teaching_backend
from agent.runtime.memory import exp_memory_permissions, teach_memory_permissions
from agent.runtime.paths import RESOURCE_DIR, memory_paths, skill_paths
from agent.runtime.prompts import load_prompt

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


def test_memory_paths_are_track_specific() -> None:
    assert memory_paths("exp") == [
        "/memory/AGENTS.md",
        "/memory/lab/AGENTS.md",
    ]
    assert memory_paths("teach") == [
        "/memory/AGENTS.md",
        "/memory/teaching/AGENTS.md",
    ]


def test_skill_paths_are_track_specific() -> None:
    assert skill_paths("exp") == ["/skills/common/", "/skills/lab/"]
    assert skill_paths("teach") == ["/skills/common/", "/skills/teaching/"]


def test_skill_discovery_matches_agent_tracks() -> None:
    exp_backend = build_exp_backend()
    teach_backend = build_teaching_backend()

    exp_skills = {
        skill["name"]
        for source in skill_paths("exp")
        for skill in _list_skills(exp_backend, source)
    }
    teach_skills = {
        skill["name"]
        for source in skill_paths("teach")
        for skill in _list_skills(teach_backend, source)
    }

    assert exp_skills == {"diagrams", "memory-maintenance", "traceroute-lab"}
    assert teach_skills == {
        "ask-question",
        "computer-networks-textbook",
        "diagrams",
        "memory-maintenance",
    }


def test_teach_memory_permissions() -> None:
    rules = teach_memory_permissions()
    operation: FilesystemOperation = "write"

    assert _check_fs_permission(rules, operation, "/memory/teaching/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/profile.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/lab/AGENTS.md") == "deny"
    assert _check_fs_permission(rules, operation, "/skills/teaching/ask-question/SKILL.md") == "deny"
    assert _check_fs_permission(rules, operation, "/root/workspace/traceroute.py") == "deny"


def test_exp_memory_permissions() -> None:
    rules = exp_memory_permissions()
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
    assert "execute" in tools
    assert "task" in tools


def test_prompt_and_skill_layout() -> None:
    assert (RESOURCE_DIR / "prompt" / "base.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "lab.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "teaching.md").is_file()
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
