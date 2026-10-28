"""账号与题库管理命令：注册接口不对外暴露，由管理员在服务器上执行。

用法（在 apps/api 下）：
    uv run python -m app.scripts.cli create-user --username student
    uv run python -m app.scripts.cli reset-password --username student
    uv run python -m app.scripts.cli disable-user --username student
    uv run python -m app.scripts.cli list-users
    uv run python -m app.scripts.cli replace-public-questions \
        --file app/data/question_bank/computer-networks-v1.json
    uv run python -m app.scripts.cli replace-public-questions --file ... --dry-run
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.question_bank import QuestionInput
from app.core.config import get_settings
from app.core.constants import (
    MAX_PASSWORD_BYTES,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
)
from app.core.database import create_db_engine, create_session_factory
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.models.user import Users
from app.repositories.user_repository import user_repository
from app.services.question_bank_service import question_bank_service


def _read_password(password: str | None) -> str:
    if password is not None:
        return password
    first = getpass.getpass("密码: ")
    second = getpass.getpass("再次输入密码: ")
    if first != second:
        raise SystemExit("两次输入的密码不一致")
    return first


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise SystemExit("密码过长（UTF-8 编码不超过 72 字节）")


def _build_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    engine = create_db_engine(settings.db.database_url)
    return create_session_factory(engine)


def cmd_create_user(args: argparse.Namespace) -> int:
    password = _read_password(args.password)
    _validate_password(password)
    factory = _build_session_factory()
    with factory() as session:
        username = args.username.strip()
        if not (MIN_USERNAME_LENGTH <= len(username) <= MAX_USERNAME_LENGTH):
            raise SystemExit(f"用户名长度须为 {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} 个字符")
        if user_repository.get_by_username(session, username) is not None:
            print(f"用户已存在: {username}", file=sys.stderr)
            return 1
        user = user_repository.create(
            session,
            username=username,
            password_hash=hash_password(password),
        )
        print(f"已创建用户: {user.username} ({user.user_id})")
    return 0


def cmd_reset_password(args: argparse.Namespace) -> int:
    password = _read_password(args.password)
    _validate_password(password)
    factory = _build_session_factory()
    with factory() as session:
        user = user_repository.get_by_username(session, args.username.strip())
        if user is None:
            print(f"用户不存在: {args.username}", file=sys.stderr)
            return 1
        user.password_hash = hash_password(password)
        session.commit()
        print(f"已重置密码: {user.username}")
    return 0


def cmd_set_status(args: argparse.Namespace, status: bool) -> int:
    factory = _build_session_factory()
    with factory() as session:
        user = user_repository.get_by_username(session, args.username.strip())
        if user is None:
            print(f"用户不存在: {args.username}", file=sys.stderr)
            return 1
        user.status = status
        session.commit()
        label = "启用" if status else "禁用"
        print(f"已{label}用户: {user.username}")
    return 0


def cmd_list_users(args: argparse.Namespace) -> int:
    factory = _build_session_factory()
    with factory() as session:
        users = list(session.scalars(select(Users).order_by(Users.username)))
        if not users:
            print("暂无用户")
            return 0
        for user in users:
            state = "启用" if user.status else "禁用"
            print(f"{user.username}\t{state}\t{user.user_id}")
    return 0


def _load_public_questions(path: Path) -> list[QuestionInput]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise SystemExit(f"文件不存在：{path}") from e
    except json.JSONDecodeError as e:
        raise SystemExit(f"文件不是合法 JSON：{path}") from e

    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise SystemExit("题库文件缺少 version=1")
    if payload.get("course") != "computer-networks":
        raise SystemExit("题库文件 course 必须是 computer-networks")
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise SystemExit("题库文件 questions 必须是非空数组")

    questions: list[QuestionInput] = []
    for index, raw in enumerate(raw_questions):
        try:
            questions.append(QuestionInput.model_validate(raw))
        except ValidationError as e:
            print(f"第 {index + 1} 题校验失败：", file=sys.stderr)
            for error in e.errors(include_input=False, include_url=False):
                location = ".".join(str(part) for part in error["loc"])
                print(f"  {location}: {error['msg']}", file=sys.stderr)
            raise SystemExit(1) from e

    seen: dict[str, int] = {}
    for index, question in enumerate(questions):
        previous = seen.get(question.stem)
        if previous is not None:
            print(
                f"题库文件存在重复题干：第 {previous + 1} 题与第 {index + 1} 题",
                file=sys.stderr,
            )
            raise SystemExit(1)
        seen[question.stem] = index
    return questions


def cmd_replace_public_questions(args: argparse.Namespace) -> int:
    questions = _load_public_questions(Path(args.file))
    factory = _build_session_factory()
    try:
        with factory() as session:
            deleted, inserted = question_bank_service.replace_public_questions(
                session,
                questions=questions,
                dry_run=args.dry_run,
            )
    except AppError as e:
        print(str(e), file=sys.stderr)
        return 1
    prefix = "dry-run: " if args.dry_run else ""
    print(f"{prefix}deleted={deleted} inserted={inserted}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="账号与题库管理命令（无注册接口）")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="创建用户")
    create.add_argument("--username", required=True)
    create.add_argument("--password", help="非交互密码（仅自动化使用，交互时省略）")
    create.set_defaults(func=cmd_create_user)

    reset = sub.add_parser("reset-password", help="重置密码")
    reset.add_argument("--username", required=True)
    reset.add_argument("--password", help="非交互密码（仅自动化使用，交互时省略）")
    reset.set_defaults(func=cmd_reset_password)

    disable = sub.add_parser("disable-user", help="禁用用户")
    disable.add_argument("--username", required=True)
    disable.set_defaults(func=lambda args: cmd_set_status(args, False))

    enable = sub.add_parser("enable-user", help="启用用户")
    enable.add_argument("--username", required=True)
    enable.set_defaults(func=lambda args: cmd_set_status(args, True))

    listing = sub.add_parser("list-users", help="列出用户")
    listing.set_defaults(func=cmd_list_users)

    replace_questions = sub.add_parser(
        "replace-public-questions",
        help="整体替换公共题库",
    )
    replace_questions.add_argument("--file", required=True, help="公共题库 JSON 文件")
    replace_questions.add_argument("--dry-run", action="store_true", help="只校验，不写库")
    replace_questions.set_defaults(func=cmd_replace_public_questions)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
