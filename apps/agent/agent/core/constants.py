from pathlib import Path

JWT_ISSUER = "computer-network-agent"
JWT_AUDIENCE = "agent"

RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources"
PROMPT_DIR = RESOURCE_DIR / "prompt"
SKILLS_DIR = RESOURCE_DIR / "skills"
