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
from agent.runtime.memory import memory_permissions
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


def test_lab_prompt_keeps_sandbox_and_experiment_skill() -> None:
    text = load_prompt("base", "lab")

    assert "AGS" in text
    assert "execute" in text
    assert "/skills/lab/traceroute-lab/SKILL.md" in text
    assert "ask_student" in text


def test_teaching_prompt_has_no_sandbox() -> None:
    text = load_prompt("base", "teaching")

    assert "没有 `execute` 工具" in text
    assert "不能运行代码" in text
    assert "teaching/learning.md" in text
    assert "AGS" not in text
    assert "/skills/lab/" not in text
    assert "traceroute" not in text


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

    assert exp_skills == {"ask-student", "memory-maintenance", "traceroute-lab"}
    assert teach_skills == {"ask-student", "memory-maintenance", "computer-networks"}


def test_teach_memory_permissions() -> None:
    rules = memory_permissions("teach")
    operation: FilesystemOperation = "write"

    assert _check_fs_permission(rules, operation, "/memory/teaching/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/profile.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/lab/AGENTS.md") == "deny"
    assert _check_fs_permission(rules, operation, "/skills/common/ask-student/SKILL.md") == "deny"
    assert _check_fs_permission(rules, operation, "/root/workspace/traceroute.py") == "deny"


def test_exp_memory_permissions() -> None:
    rules = memory_permissions("exp")
    operation: FilesystemOperation = "write"

    assert _check_fs_permission(rules, operation, "/memory/lab/learning.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/AGENTS.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/profile.md") == "allow"
    assert _check_fs_permission(rules, operation, "/memory/teaching/AGENTS.md") == "deny"
    assert _check_fs_permission(rules, operation, "/skills/common/ask-student/SKILL.md") == "deny"
    assert _check_fs_permission(rules, operation, "/root/workspace/traceroute.py") == "allow"


def test_teach_graph_has_no_execute_but_keeps_task(monkeypatch: pytest.MonkeyPatch) -> None:
    tools = _tool_names(_build_teach_graph(monkeypatch))

    assert "ask_student" in tools
    assert "read_file" in tools
    assert "write_file" in tools
    assert "execute" not in tools
    assert "task" in tools


def test_exp_graph_keeps_execute_and_task(monkeypatch: pytest.MonkeyPatch) -> None:
    tools = _tool_names(_build_exp_graph(monkeypatch))

    assert "ask_student" in tools
    assert "execute" in tools
    assert "task" in tools


def test_prompt_and_skill_layout() -> None:
    assert (RESOURCE_DIR / "prompt" / "base.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "lab.md").is_file()
    assert (RESOURCE_DIR / "prompt" / "teaching.md").is_file()
    assert not (RESOURCE_DIR / "prompt" / "system.md").exists()

    assert (RESOURCE_DIR / "skills" / "common" / "ask-student" / "SKILL.md").is_file()
    assert (RESOURCE_DIR / "skills" / "common" / "memory-maintenance" / "SKILL.md").is_file()
    assert (RESOURCE_DIR / "skills" / "lab" / "traceroute-lab" / "SKILL.md").is_file()
    assert (
        RESOURCE_DIR / "skills" / "lab" / "traceroute-lab" / "chapters" / "01-认识-traceroute.md"
    ).is_file()
    assert (RESOURCE_DIR / "skills" / "teaching" / "computer-networks" / "SKILL.md").is_file()
    assert (
        RESOURCE_DIR / "skills" / "teaching" / "computer-networks" / "textbook" / "00-index.md"
    ).is_file()
    assert not (RESOURCE_DIR / "materials").exists()
    assert not (RESOURCE_DIR / "skills" / "ask-student").exists()
    assert not (RESOURCE_DIR / "skills" / "memory-maintenance").exists()
    assert not (RESOURCE_DIR / "skills" / "traceroute-lab").exists()


def test_langgraph_registers_both_agents() -> None:
    config = json.loads((APP_DIR / "langgraph.json").read_text())

    assert config["graphs"]["exp_agent"] == "./agent/main.py:build_exp_agent"
    assert config["graphs"]["teach_agent"] == "./agent/main.py:build_teach_agent"


def test_docker_image_serves_both_agents() -> None:
    dockerfile = (APP_DIR.parents[1] / "deploy" / "docker" / "agent.Dockerfile").read_text()

    assert '"exp_agent"' in dockerfile
    assert '"teach_agent"' in dockerfile
