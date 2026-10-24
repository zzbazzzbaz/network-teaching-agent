"""账号管理命令：注册接口不对外暴露，由管理员在服务器上建号。

用法（在 apps/api 下）：
    uv run python -m scripts.cli create-user --username student
    uv run python -m scripts.cli reset-password --username student
    uv run python -m scripts.cli disable-user --username student
    uv run python -m scripts.cli list-users
"""

import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings
from core.constants import (
    MAX_PASSWORD_BYTES,
    MAX_USERNAME_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
)
from core.database import create_all, create_db_engine, create_session_factory
from core.security import hash_password
from models.user import Users
from repositories.user_repository import user_repository


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
    create_all(engine)
    return create_session_factory(engine)


def cmd_create_user(args: argparse.Namespace) -> int:
    password = _read_password(args.password)
    _validate_password(password)
    factory = _build_session_factory()
    with factory() as session:
        username = args.username.strip()
        if not (MIN_USERNAME_LENGTH <= len(username) <= MAX_USERNAME_LENGTH):
            raise SystemExit(
                f"用户名长度须为 {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} 个字符"
            )
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="用户管理命令（无注册接口）")
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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
