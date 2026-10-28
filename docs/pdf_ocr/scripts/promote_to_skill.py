#!/usr/bin/env python3
"""Copy validated generated resources into the teach_agent skill directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import GENERATED_DIR, ensure_dirs, fail

DEFAULT_TARGET = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "agent"
    / "agent"
    / "resources"
    / "skills"
    / "teaching"
    / "computer-networks"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=GENERATED_DIR / "computer-networks")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--clean", action="store_true", help="replace target directory")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    source = args.source
    target = args.target
    if not (source / "SKILL.md").is_file():
        fail(f"generated skill not found: {source}")
    print(f"source: {source}")
    print(f"target: {target}")
    if args.dry_run:
        return
    if args.clean and target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    print("promoted")


if __name__ == "__main__":
    main()
