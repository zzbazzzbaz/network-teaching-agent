"""API 进程内定时任务调度。

API 以单容器单进程部署，sandbox reaper 由进程内的 APScheduler 触发，不再依赖
独立的 reaper 容器或宿主机 cron。多副本部署时必须只让一个副本启用调度。
"""

from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.job.sandbox_reaper import run_reaper_job

SANDBOX_REAPER_JOB_ID = "sandbox-reaper"


def build_scheduler(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_reaper_job,
        trigger="interval",
        seconds=settings.scheduler.reaper_interval_seconds,
        kwargs={"settings": settings, "session_factory": session_factory},
        id=SANDBOX_REAPER_JOB_ID,
        name="sandbox reaper",
        # 默认 1 秒内未执行会跳过；回收任务允许延迟补跑一次。
        misfire_grace_time=None,
        next_run_time=datetime.now(UTC),
    )
    return scheduler
