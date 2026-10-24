import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from e2b import Sandbox, SandboxException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.gateway.ags import connect_sandbox, create_sandbox, sandbox_host
from app.models.user_sandbox import UserSandbox
from app.repositories.user_repository import user_repository
from app.repositories.user_sandbox_repository import user_sandbox_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SandboxInfo:
    sandbox_id: str
    vscode_url: str
    ttyd_url: str
    expires_at: datetime


def get_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    record = user_sandbox_repository.get(session, user_id)
    if record is None:
        raise NotFoundError("沙箱未启动")

    if record.expires_at <= datetime.now(UTC):
        _clear_record(session, record)
        raise NotFoundError("沙箱已过期")

    try:
        sandbox = connect_sandbox(settings, record.sandbox_id)
        if not sandbox.is_running():
            raise SandboxException("sandbox is not running")
    except SandboxException as e:
        logger.info("沙箱不可用，清理记录", exc_info=True)
        _clear_record(session, record)
        raise NotFoundError("沙箱不可用") from e

    return _build_info(sandbox, record.expires_at)


def ensure_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    user = user_repository.get_for_update(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")

    now = datetime.now(UTC)
    timeout = settings.ags.sandbox_timeout_seconds
    record = user_sandbox_repository.get(session, user_id)
    old_sandbox_id = record.sandbox_id if record is not None else None

    if record is not None and record.expires_at > now:
        try:
            sandbox = connect_sandbox(settings, record.sandbox_id)
            if not sandbox.is_running():
                raise SandboxException("sandbox is not running")
            sandbox.set_timeout(timeout)
        except SandboxException:
            logger.info("复用沙箱失败，创建新沙箱", exc_info=True)
        else:
            expires_at = now + timedelta(seconds=timeout)
            user_sandbox_repository.save(
                session,
                user_id=user_id,
                sandbox_id=record.sandbox_id,
                expires_at=expires_at,
            )
            session.commit()
            return _build_info(sandbox, expires_at)

    try:
        sandbox = create_sandbox(settings, user_id=str(user_id))
    except SandboxException as e:
        session.rollback()
        raise ServiceUnavailableError("沙箱启动失败") from e

    expires_at = datetime.now(UTC) + timedelta(seconds=timeout)
    try:
        user_sandbox_repository.save(
            session,
            user_id=user_id,
            sandbox_id=sandbox.sandbox_id,
            expires_at=expires_at,
        )
        session.commit()
    except Exception:
        session.rollback()
        try:
            sandbox.kill()
        except Exception:
            logger.warning("清理创建失败的沙箱时出错", exc_info=True)
        raise

    if old_sandbox_id is not None and old_sandbox_id != sandbox.sandbox_id:
        _stop_best_effort(settings, old_sandbox_id)

    return _build_info(sandbox, expires_at)


def delete_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> None:
    user = user_repository.get_for_update(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")

    record = user_sandbox_repository.get(session, user_id)
    if record is None:
        return

    _stop_best_effort(settings, record.sandbox_id)
    user_sandbox_repository.delete(session, record)
    session.commit()


def _clear_record(session: Session, record: UserSandbox) -> None:
    user_sandbox_repository.delete(session, record)
    session.commit()


def _stop_best_effort(settings: Settings, sandbox_id: str) -> None:
    try:
        sandbox = connect_sandbox(settings, sandbox_id)
        sandbox.kill()
    except Exception:
        logger.warning("停止沙箱失败", exc_info=True)


def _build_info(sandbox: Sandbox, expires_at: datetime) -> SandboxInfo:
    host = sandbox_host(sandbox)
    return SandboxInfo(
        sandbox_id=sandbox.sandbox_id,
        vscode_url=f"https://{host}/vscode/",
        ttyd_url=f"https://{host}/ttyd/",
        expires_at=expires_at,
    )
