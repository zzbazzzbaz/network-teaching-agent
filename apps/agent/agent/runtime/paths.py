from pathlib import Path
from typing import Literal

RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"
PROMPT_DIR = RESOURCE_DIR / "prompt"

AgentName = Literal["exp", "teach"]

MEMORY_PATHS: dict[AgentName, list[str]] = {
    "exp": ["/memory/AGENTS.md", "/memory/lab/AGENTS.md"],
    "teach": ["/memory/AGENTS.md", "/memory/teaching/AGENTS.md"],
}

SKILLS_PATHS: dict[AgentName, list[str]] = {
    "exp": ["/skills/common/", "/skills/lab/"],
    "teach": ["/skills/common/", "/skills/teaching/"],
}


def memory_paths(agent: AgentName) -> list[str]:
    return list(MEMORY_PATHS[agent])


def skill_paths(agent: AgentName) -> list[str]:
    return list(SKILLS_PATHS[agent])
