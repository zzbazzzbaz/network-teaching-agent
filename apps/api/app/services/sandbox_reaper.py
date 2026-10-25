import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user_sandbox import SandboxStatus
from app.repositories.user_sandbox_repository import user_sandbox_repository
from app.services.sandbox_lifecycle import SandboxPolicy
from app.services.sandbox_service import (
    SandboxOpResult,
    destroy_record,
    drop_record,
    pause_record,
)

logger = logging.getLogger(__name__)

REAP_BATCH_SIZE = 20


@dataclass(slots=True)
class ReaperStats:
    paused: int = 0
    destroyed: int = 0
    cleared: int = 0
    failed: int = 0


def reap_sandboxes(
    *,
    session: Session,
    settings: Settings,
    now: datetime | None = None,
    limit: int = REAP_BATCH_SIZE,
) -> ReaperStats:
    """扫描并处理到期沙箱。每类最多处理 limit 条。"""
    current = now if now is not None else datetime.now(UTC)
    policy = SandboxPolicy.from_settings(settings)
    stats = ReaperStats()

    destroy_attempted: set[uuid.UUID] = set()
    _destroy_over_lifetime(session, settings, current, limit, destroy_attempted, stats)
    _retry_stopping(session, settings, limit, destroy_attempted, stats)
    _destroy_paused_expired(
        session, settings, policy, current, limit, destroy_attempted, stats
    )

    pause_attempted: set[uuid.UUID] = set()
    _pause_idle(session, settings, policy, current, limit, pause_attempted, stats)

    return stats


def _destroy_over_lifetime(
    session: Session,
    settings: Settings,
    now: datetime,
    limit: int,
    attempted: set[uuid.UUID],
    stats: ReaperStats,
) -> None:
    for _ in range(limit):
        record = user_sandbox_repository.claim_over_lifetime(
            session,
            now=now,
            exclude=attempted,
        )
        if record is None:
            return
        attempted.add(record.user_id)
        if destroy_record(session, settings, record) is SandboxOpResult.FAILED:
            stats.failed += 1
        else:
            stats.destroyed += 1


def _retry_stopping(
    session: Session,
    settings: Settings,
    limit: int,
    attempted: set[uuid.UUID],
    stats: ReaperStats,
) -> None:
    for _ in range(limit):
        record = user_sandbox_repository.claim_stopping(
            session,
            exclude=attempted,
        )
        if record is None:
            return
        attempted.add(record.user_id)
        if destroy_record(session, settings, record) is SandboxOpResult.FAILED:
            stats.failed += 1
        else:
            stats.destroyed += 1


def _destroy_paused_expired(
    session: Session,
    settings: Settings,
    policy: SandboxPolicy,
    now: datetime,
    limit: int,
    attempted: set[uuid.UUID],
    stats: ReaperStats,
) -> None:
    for _ in range(limit):
        record = user_sandbox_repository.claim_paused_expired(
            session,
            paused_before=policy.paused_before(now),
            exclude=attempted,
        )
        if record is None:
            return
        attempted.add(record.user_id)
        if destroy_record(session, settings, record) is SandboxOpResult.FAILED:
            stats.failed += 1
        else:
            stats.destroyed += 1


def _pause_idle(
    session: Session,
    settings: Settings,
    policy: SandboxPolicy,
    now: datetime,
    limit: int,
    attempted: set[uuid.UUID],
    stats: ReaperStats,
) -> None:
    for _ in range(limit):
        record = user_sandbox_repository.claim_idle_running(
            session,
            idle_before=policy.idle_before(now),
            now=now,
            exclude=attempted,
        )
        if record is None:
            return
        attempted.add(record.user_id)

        result = pause_record(settings, record)
        if result is SandboxOpResult.GONE:
            logger.info(
                "reaper 清理不存在的沙箱 user_id=%s sandbox_id=%s action=pause",
                record.user_id,
                record.sandbox_id,
            )
            drop_record(session, record)
            stats.cleared += 1
        elif result is SandboxOpResult.FAILED:
            session.rollback()
            stats.failed += 1
        else:
            record.status = SandboxStatus.PAUSED.value
            record.paused_at = now
            session.commit()
            stats.paused += 1
            logger.info(
                "reaper 暂停成功 user_id=%s sandbox_id=%s from_status=running"
                " to_status=paused action=pause",
                record.user_id,
                record.sandbox_id,
            )
