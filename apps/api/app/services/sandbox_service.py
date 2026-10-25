import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from e2b import SandboxNotFoundException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.gateway.ags import (
    connect_sandbox,
    create_sandbox,
    kill_sandbox,
    pause_sandbox,
    sandbox_host,
)
from app.models.user_sandbox import SandboxStatus, UserSandbox
from app.repositories.user_repository import user_repository
from app.repositories.user_sandbox_repository import user_sandbox_repository
from app.services.sandbox_lifecycle import SandboxPolicy

logger = logging.getLogger(__name__)

MAX_ENSURE_ATTEMPTS = 2


class SandboxOpResult(StrEnum):
    OK = "ok"
    GONE = "gone"
    FAILED = "failed"


class DeleteResult(StrEnum):
    DELETED = "deleted"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True)
class SandboxInfo:
    sandbox_id: str
    status: SandboxStatus
    vscode_url: str | None
    ttyd_url: str | None
    expires_at: datetime
    last_active_at: datetime
    paused_at: datetime | None
    hard_destroy_at: datetime
    heartbeat_seconds: int


def get_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    """只读数据库；不连接 AGS，也不清理记录。"""
    record = _require_record(user_sandbox_repository.get(session, user_id))
    return _build_info(settings, SandboxPolicy.from_settings(settings), record)


def ensure_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    now = datetime.now(UTC)
    policy = SandboxPolicy.from_settings(settings)

    # destroy/drop 需要先 commit 才能保证崩溃安全，这会释放 users 行锁；
    # 因此轮换或清理后重新加锁并读取，避免并发请求重复创建。
    for _ in range(MAX_ENSURE_ATTEMPTS):
        record = _lock_record(session, user_id)

        if record is None:
            return create_record(
                user_id=user_id,
                session=session,
                settings=settings,
                policy=policy,
                now=now,
            )

        _reject_stopping(record)
        if policy.needs_rotation(record, now):
            reason = (
                "max_lifetime"
                if policy.is_over_lifetime(record, now)
                else "paused_retention"
            )
            logger.info(
                "沙箱需要轮换 user_id=%s sandbox_id=%s reason=%s",
                user_id,
                record.sandbox_id,
                reason,
            )
            if destroy_record(session, settings, record) is SandboxOpResult.FAILED:
                raise ServiceUnavailableError("沙箱销毁失败，请稍后重试")
            continue

        result = resume_record(settings, record, policy)
        if result is SandboxOpResult.GONE:
            logger.info(
                "沙箱不存在，清理后重建 user_id=%s sandbox_id=%s",
                user_id,
                record.sandbox_id,
            )
            drop_record(session, record)
            continue
        if result is SandboxOpResult.FAILED:
            raise ServiceUnavailableError("沙箱连接失败，请稍后重试")

        _touch(record, now, policy)
        session.commit()
        return _build_info(settings, policy, record)

    raise ServiceUnavailableError("沙箱状态变化频繁，请稍后重试")


def heartbeat_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    now = datetime.now(UTC)
    policy = SandboxPolicy.from_settings(settings)
    record = _require_record(_lock_record(session, user_id))
    _reject_stopping(record)
    if record.state is SandboxStatus.PAUSED:
        return _build_info(settings, policy, record)

    result = resume_record(settings, record, policy)
    if result is SandboxOpResult.GONE:
        logger.info(
            "心跳发现沙箱不存在，清理记录 user_id=%s sandbox_id=%s",
            user_id,
            record.sandbox_id,
        )
        drop_record(session, record)
        raise NotFoundError("沙箱不存在，请重新启动")
    if result is SandboxOpResult.FAILED:
        raise ServiceUnavailableError("沙箱续期失败，请稍后重试")

    _touch(record, now, policy)
    session.commit()
    return _build_info(settings, policy, record)


def pause_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    now = datetime.now(UTC)
    policy = SandboxPolicy.from_settings(settings)
    record = _require_record(_lock_record(session, user_id))
    _reject_stopping(record)
    if record.state is SandboxStatus.PAUSED:
        return _build_info(settings, policy, record)

    result = pause_record(settings, record)
    if result is SandboxOpResult.GONE:
        logger.info(
            "暂停时发现沙箱不存在，清理记录 user_id=%s sandbox_id=%s",
            user_id,
            record.sandbox_id,
        )
        drop_record(session, record)
        raise NotFoundError("沙箱不存在")
    if result is SandboxOpResult.FAILED:
        raise ServiceUnavailableError("沙箱暂停失败，请稍后重试")

    record.status = SandboxStatus.PAUSED.value
    record.paused_at = now
    session.commit()
    return _build_info(settings, policy, record)


def delete_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> DeleteResult:
    record = _lock_record(session, user_id)
    if record is None:
        return DeleteResult.DELETED
    if record.state is SandboxStatus.STOPPING:
        return DeleteResult.STOPPING

    if destroy_record(session, settings, record) is SandboxOpResult.FAILED:
        raise ServiceUnavailableError("沙箱销毁失败，请稍后重试")
    return DeleteResult.DELETED


def resume_record(
    settings: Settings,
    record: UserSandbox,
    policy: SandboxPolicy,
) -> SandboxOpResult:
    """连接并续期 AGS 沙箱；不修改数据库。"""
    try:
        connect_sandbox(
            settings,
            record.sandbox_id,
            timeout=policy.timeout_seconds,
        )
    except SandboxNotFoundException:
        return SandboxOpResult.GONE
    except Exception:
        logger.warning(
            "连接沙箱失败 user_id=%s sandbox_id=%s",
            record.user_id,
            record.sandbox_id,
            exc_info=True,
        )
        return SandboxOpResult.FAILED
    return SandboxOpResult.OK


def pause_record(settings: Settings, record: UserSandbox) -> SandboxOpResult:
    """暂停 AGS 沙箱；不修改数据库。"""
    try:
        # SDK 约定 False 表示沙箱已经是 paused，属于幂等成功。
        pause_sandbox(settings, record.sandbox_id)
    except SandboxNotFoundException:
        return SandboxOpResult.GONE
    except Exception:
        logger.warning(
            "暂停沙箱失败 user_id=%s sandbox_id=%s",
            record.user_id,
            record.sandbox_id,
            exc_info=True,
        )
        return SandboxOpResult.FAILED
    return SandboxOpResult.OK


def destroy_record(
    session: Session,
    settings: Settings,
    record: UserSandbox,
) -> SandboxOpResult:
    """先提交 stopping 意图，再 kill 并删除记录；失败时保留 stopping 供重试。"""
    user_id = record.user_id
    sandbox_id = record.sandbox_id
    from_status = record.status

    record.status = SandboxStatus.STOPPING.value
    session.commit()

    try:
        # SDK 约定 False 表示沙箱已经不存在，可以直接清理记录。
        kill_sandbox(settings, sandbox_id)
    except SandboxNotFoundException:
        pass
    except Exception as e:
        session.rollback()
        logger.warning(
            "销毁沙箱失败 user_id=%s sandbox_id=%s from_status=%s error=%s",
            user_id,
            sandbox_id,
            from_status,
            e,
            exc_info=True,
        )
        return SandboxOpResult.FAILED

    try:
        user_sandbox_repository.delete(session, record)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(
            "删除沙箱记录失败 user_id=%s sandbox_id=%s from_status=%s error=%s",
            user_id,
            sandbox_id,
            from_status,
            e,
            exc_info=True,
        )
        return SandboxOpResult.FAILED

    logger.info(
        "沙箱销毁成功 user_id=%s sandbox_id=%s from_status=%s to_status=absent",
        user_id,
        sandbox_id,
        from_status,
    )
    return SandboxOpResult.OK


def drop_record(session: Session, record: UserSandbox) -> None:
    user_sandbox_repository.delete(session, record)
    session.commit()


def create_record(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
    policy: SandboxPolicy,
    now: datetime,
) -> SandboxInfo:
    try:
        sandbox = create_sandbox(settings, user_id=str(user_id))
    except Exception as e:
        session.rollback()
        logger.warning("创建沙箱失败 user_id=%s", user_id, exc_info=True)
        raise ServiceUnavailableError("沙箱启动失败") from e

    try:
        record = user_sandbox_repository.create(
            session,
            user_id=user_id,
            sandbox_id=sandbox.sandbox_id,
            status=SandboxStatus.RUNNING,
            last_active_at=now,
            paused_at=None,
            expires_at=policy.expires_at(now),
            hard_destroy_at=policy.hard_destroy_at(now),
        )
        session.commit()
    except Exception:
        session.rollback()
        _kill_quietly(settings, sandbox.sandbox_id)
        raise

    return _build_info(settings, policy, record)


def _lock_owner(session: Session, user_id: uuid.UUID) -> None:
    if user_repository.get_for_update(session, user_id) is None:
        raise NotFoundError("用户不存在")


def _lock_record(session: Session, user_id: uuid.UUID) -> UserSandbox | None:
    _lock_owner(session, user_id)
    return user_sandbox_repository.get_for_update(session, user_id)


def _require_record(record: UserSandbox | None) -> UserSandbox:
    if record is None:
        raise NotFoundError("沙箱未启动")
    return record


def _reject_stopping(record: UserSandbox) -> None:
    if record.state is SandboxStatus.STOPPING:
        raise ConflictError("沙箱正在销毁，请稍后重试")


def _touch(record: UserSandbox, now: datetime, policy: SandboxPolicy) -> None:
    record.status = SandboxStatus.RUNNING.value
    record.paused_at = None
    record.last_active_at = now
    record.expires_at = policy.expires_at(now)


def _kill_quietly(settings: Settings, sandbox_id: str) -> None:
    try:
        kill_sandbox(settings, sandbox_id)
    except Exception:
        logger.warning(
            "清理创建失败的沙箱时出错 sandbox_id=%s",
            sandbox_id,
            exc_info=True,
        )


def _build_info(
    settings: Settings,
    policy: SandboxPolicy,
    record: UserSandbox,
) -> SandboxInfo:
    host = sandbox_host(settings, record.sandbox_id)
    state = record.state
    running = state is SandboxStatus.RUNNING
    return SandboxInfo(
        sandbox_id=record.sandbox_id,
        status=state,
        vscode_url=f"https://{host}/vscode/" if running else None,
        ttyd_url=f"https://{host}/ttyd/" if running else None,
        expires_at=record.expires_at,
        last_active_at=record.last_active_at,
        paused_at=record.paused_at,
        hard_destroy_at=record.hard_destroy_at,
        heartbeat_seconds=policy.heartbeat_seconds,
    )
