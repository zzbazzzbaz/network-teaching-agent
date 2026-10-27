from agent.runtime.paths import PROMPT_DIR


def load_prompt(*parts: str) -> str:
    return "\n\n".join(
        (PROMPT_DIR / f"{part}.md").read_text(encoding="utf-8").strip() for part in parts
    )
