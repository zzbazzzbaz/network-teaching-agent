import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from e2b import SandboxException, SandboxNotFoundException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.gateway.ags import connect_sandbox, create_sandbox, kill_sandbox, sandbox_host
from app.models.user_sandbox import UserSandbox
from app.repositories.user_repository import user_repository
from app.repositories.user_sandbox_repository import user_sandbox_repository

logger = logging.getLogger(__name__)

SandboxStatus = Literal["running", "paused", "stopping"]


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


@dataclass(slots=True)
class ReaperStats:
    paused: int = 0
    destroyed: int = 0
    cleared: int = 0
    failed: int = 0


def get_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    """只读数据库；不连接 AGS，也不清理记录。"""
    record = user_sandbox_repository.get(session, user_id)
    if record is None:
        raise NotFoundError("沙箱未启动")
    return _build_info(settings, record)


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
    record = user_sandbox_repository.get_for_update(session, user_id)

    if record is not None:
        if record.status == "stopping":
            session.commit()
            raise ConflictError("沙箱正在销毁，请稍后重试")

        if record.hard_destroy_at <= now:
            logger.info(
                "沙箱超过最长寿命，销毁后重建 user_id=%s sandbox_id=%s",
                user_id,
                record.sandbox_id,
            )
            _destroy_record(session, settings, record)
            record = None
        elif _paused_expired(record, now, settings):
            logger.info(
                "沙箱超过暂停保留期，销毁后重建 user_id=%s sandbox_id=%s",
                user_id,
                record.sandbox_id,
            )
            _destroy_record(session, settings, record)
            record = None

    if record is not None:
        try:
            sandbox = connect_sandbox(settings, record.sandbox_id)
            sandbox.set_timeout(timeout)
        except SandboxNotFoundException:
            logger.info(
                "沙箱不存在，清理后重建 user_id=%s sandbox_id=%s",
                user_id,
                record.sandbox_id,
            )
            _drop_record(session, record)
            record = None
        except Exception as e:
            raise ServiceUnavailableError("沙箱连接失败，请稍后重试") from e
        else:
            _mark_running(record, now, timeout)
            session.commit()
            return _build_info(settings, record)

    return _create_sandbox_record(
        user_id=user_id,
        session=session,
        settings=settings,
        now=now,
    )


def heartbeat_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    user = user_repository.get_for_update(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")

    record = user_sandbox_repository.get_for_update(session, user_id)
    if record is None:
        raise NotFoundError("沙箱未启动")
    if record.status == "stopping":
        session.commit()
        raise ConflictError("沙箱正在销毁，请稍后重试")
    if record.status == "paused":
        session.commit()
        return _build_info(settings, record)

    now = datetime.now(UTC)
    timeout = settings.ags.sandbox_timeout_seconds
    try:
        sandbox = connect_sandbox(settings, record.sandbox_id)
        sandbox.set_timeout(timeout)
    except SandboxNotFoundException as e:
        raise ServiceUnavailableError("沙箱不存在，请重新启动") from e
    except Exception as e:
        raise ServiceUnavailableError("沙箱续期失败，请稍后重试") from e

    record.last_active_at = now
    record.expires_at = now + timedelta(seconds=timeout)
    session.commit()
    return _build_info(settings, record)


def pause_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> SandboxInfo:
    user = user_repository.get_for_update(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")

    record = user_sandbox_repository.get_for_update(session, user_id)
    if record is None:
        raise NotFoundError("沙箱未启动")
    if record.status == "stopping":
        session.commit()
        raise ConflictError("沙箱正在销毁，请稍后重试")
    if record.status == "paused":
        session.commit()
        return _build_info(settings, record)

    try:
        sandbox = connect_sandbox(settings, record.sandbox_id)
        if not sandbox.pause():
            raise SandboxException("pause returned false")
    except SandboxNotFoundException as e:
        _drop_record(session, record)
        raise NotFoundError("沙箱不存在") from e
    except Exception as e:
        logger.warning(
            "暂停沙箱失败 user_id=%s sandbox_id=%s",
            user_id,
            record.sandbox_id,
            exc_info=True,
        )
        raise ServiceUnavailableError("沙箱暂停失败，请稍后重试") from e

    record.status = "paused"
    record.paused_at = datetime.now(UTC)
    session.commit()
    return _build_info(settings, record)


def delete_user_sandbox(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
) -> bool:
    """销毁沙箱。返回 True 表示已删除记录，False 表示已经在 stopping。"""
    user = user_repository.get_for_update(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")

    record = user_sandbox_repository.get_for_update(session, user_id)
    if record is None:
        session.commit()
        return True
    if record.status == "stopping":
        session.commit()
        return False

    _destroy_record(session, settings, record)
    return True


def reap_sandboxes(
    *,
    session: Session,
    settings: Settings,
    now: datetime | None = None,
    limit: int = 20,
) -> ReaperStats:
    """扫描并处理到期沙箱。每类最多处理 limit 条。"""
    current = now if now is not None else datetime.now(UTC)
    stats = ReaperStats()
    idle_before = current - timedelta(seconds=settings.ags.sandbox_idle_seconds)
    paused_before = current - timedelta(
        seconds=settings.ags.sandbox_paused_retention_seconds
    )

    pause_attempted: set[uuid.UUID] = set()
    for _ in range(limit):
        record = _claim_one(
            session,
            UserSandbox.status == "running",
            UserSandbox.last_active_at <= idle_before,
            UserSandbox.hard_destroy_at > current,
            order_by=UserSandbox.last_active_at,
            exclude=pause_attempted,
        )
        if record is None:
            break
        pause_attempted.add(record.user_id)
        _reap_pause(session, settings, record, current, stats)

    destroy_attempted: set[uuid.UUID] = set()
    for _ in range(limit):
        record = _claim_one(
            session,
            UserSandbox.status == "paused",
            UserSandbox.paused_at.is_not(None),
            UserSandbox.paused_at <= paused_before,
            order_by=UserSandbox.paused_at,
            exclude=destroy_attempted,
        )
        if record is None:
            break
        destroy_attempted.add(record.user_id)
        _reap_destroy(session, settings, record, stats)

    for _ in range(limit):
        record = _claim_one(
            session,
            UserSandbox.status.in_(("running", "paused")),
            UserSandbox.hard_destroy_at <= current,
            order_by=UserSandbox.hard_destroy_at,
            exclude=destroy_attempted,
        )
        if record is None:
            break
        destroy_attempted.add(record.user_id)
        _reap_destroy(session, settings, record, stats)

    for _ in range(limit):
        record = _claim_one(
            session,
            UserSandbox.status == "stopping",
            order_by=UserSandbox.updated_at,
            exclude=destroy_attempted,
        )
        if record is None:
            break
        destroy_attempted.add(record.user_id)
        _reap_destroy(session, settings, record, stats)

    return stats


def _claim_one(
    session: Session,
    *conditions: ColumnElement[bool],
    order_by: InstrumentedAttribute[Any],
    exclude: set[uuid.UUID] | None = None,
) -> UserSandbox | None:
    query = select(UserSandbox).where(*conditions)
    if exclude:
        query = query.where(UserSandbox.user_id.not_in(exclude))
    return session.scalar(
        query.order_by(order_by).with_for_update(skip_locked=True).limit(1)
    )


def _reap_pause(
    session: Session,
    settings: Settings,
    record: UserSandbox,
    now: datetime,
    stats: ReaperStats,
) -> None:
    user_id = record.user_id
    sandbox_id = record.sandbox_id
    try:
        sandbox = connect_sandbox(settings, sandbox_id)
        if not sandbox.pause():
            raise SandboxException("pause returned false")
    except SandboxNotFoundException:
        logger.info(
            "reaper 清理不存在的沙箱 user_id=%s sandbox_id=%s action=pause",
            user_id,
            sandbox_id,
        )
        _drop_record(session, record)
        stats.cleared += 1
        return
    except Exception as e:
        session.rollback()
        stats.failed += 1
        logger.warning(
            "reaper 暂停失败 user_id=%s sandbox_id=%s from_status=running"
            " to_status=running action=pause error=%s",
            user_id,
            sandbox_id,
            e,
            exc_info=True,
        )
        return

    record.status = "paused"
    record.paused_at = now
    session.commit()
    stats.paused += 1
    logger.info(
        "reaper 暂停成功 user_id=%s sandbox_id=%s from_status=running"
        " to_status=paused action=pause",
        user_id,
        sandbox_id,
    )


def _reap_destroy(
    session: Session,
    settings: Settings,
    record: UserSandbox,
    stats: ReaperStats,
) -> None:
    user_id = record.user_id
    sandbox_id = record.sandbox_id
    from_status = record.status
    if record.status != "stopping":
        record.status = "stopping"
    session.commit()

    try:
        _kill_sandbox(settings, sandbox_id)
    except Exception as e:
        stats.failed += 1
        logger.warning(
            "reaper 销毁失败 user_id=%s sandbox_id=%s from_status=%s"
            " to_status=stopping action=destroy error=%s",
            user_id,
            sandbox_id,
            from_status,
            e,
            exc_info=True,
        )
        return

    user_sandbox_repository.delete(session, record)
    session.commit()
    stats.destroyed += 1
    logger.info(
        "reaper 销毁成功 user_id=%s sandbox_id=%s from_status=%s"
        " to_status=absent action=destroy",
        user_id,
        sandbox_id,
        from_status,
    )


def _create_sandbox_record(
    *,
    user_id: uuid.UUID,
    session: Session,
    settings: Settings,
    now: datetime,
) -> SandboxInfo:
    timeout = settings.ags.sandbox_timeout_seconds
    try:
        sandbox = create_sandbox(settings, user_id=str(user_id))
    except Exception as e:
        session.rollback()
        raise ServiceUnavailableError("沙箱启动失败") from e

    expires_at = now + timedelta(seconds=timeout)
    hard_destroy_at = now + timedelta(seconds=settings.ags.sandbox_max_lifetime_seconds)
    try:
        record = user_sandbox_repository.save(
            session,
            user_id=user_id,
            sandbox_id=sandbox.sandbox_id,
            status="running",
            last_active_at=now,
            paused_at=None,
            expires_at=expires_at,
            hard_destroy_at=hard_destroy_at,
        )
        session.commit()
    except Exception:
        session.rollback()
        try:
            _kill_sandbox(settings, sandbox.sandbox_id)
        except Exception:
            logger.warning("清理创建失败的沙箱时出错", exc_info=True)
        raise

    return _build_info(settings, record)


def _destroy_record(session: Session, settings: Settings, record: UserSandbox) -> None:
    record.status = "stopping"
    session.commit()

    try:
        _kill_sandbox(settings, record.sandbox_id)
    except Exception as e:
        logger.warning(
            "销毁沙箱失败 user_id=%s sandbox_id=%s，保留 stopping",
            record.user_id,
            record.sandbox_id,
            exc_info=True,
        )
        raise ServiceUnavailableError("沙箱销毁失败，请稍后重试") from e

    user_sandbox_repository.delete(session, record)
    session.commit()


def _kill_sandbox(settings: Settings, sandbox_id: str) -> None:
    try:
        kill_sandbox(settings, sandbox_id)
    except SandboxNotFoundException:
        return


def _drop_record(session: Session, record: UserSandbox) -> None:
    user_sandbox_repository.delete(session, record)
    session.commit()


def _mark_running(record: UserSandbox, now: datetime, timeout: int) -> None:
    record.status = "running"
    record.paused_at = None
    record.last_active_at = now
    record.expires_at = now + timedelta(seconds=timeout)


def _paused_expired(record: UserSandbox, now: datetime, settings: Settings) -> bool:
    if record.status != "paused" or record.paused_at is None:
        return False
    retention = timedelta(seconds=settings.ags.sandbox_paused_retention_seconds)
    return record.paused_at <= now - retention


def _build_info(settings: Settings, record: UserSandbox) -> SandboxInfo:
    host = sandbox_host(settings, record.sandbox_id)
    running = record.status == "running"
    return SandboxInfo(
        sandbox_id=record.sandbox_id,
        status=cast(SandboxStatus, record.status),
        vscode_url=f"https://{host}/vscode/" if running else None,
        ttyd_url=f"https://{host}/ttyd/" if running else None,
        expires_at=record.expires_at,
        last_active_at=record.last_active_at,
        paused_at=record.paused_at,
        hard_destroy_at=record.hard_destroy_at,
        heartbeat_seconds=settings.ags.sandbox_heartbeat_seconds,
    )
