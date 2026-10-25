"""沙箱生命周期回收任务。

仅由 API 进程内的 APScheduler 触发，每轮执行一次回收。
"""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.services import sandbox_reaper

logger = logging.getLogger(__name__)


def run_reaper_job(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> sandbox_reaper.ReaperStats:
    with session_factory() as session:
        stats = sandbox_reaper.reap_sandboxes(
            session=session,
            settings=settings,
        )
    logger.info(
        "sandbox reaper: paused=%s destroyed=%s cleared=%s failed=%s",
        stats.paused,
        stats.destroyed,
        stats.cleared,
        stats.failed,
    )
    return stats
