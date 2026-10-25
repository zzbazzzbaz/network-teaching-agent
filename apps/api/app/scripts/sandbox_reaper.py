"""沙箱生命周期回收任务。

用法（在 apps/api 下）：
    uv run python -m app.scripts.sandbox_reaper --once
    uv run python -m app.scripts.sandbox_reaper
"""

import argparse
import logging
import time

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import create_db_engine, create_session_factory
from app.services import sandbox_service

logger = logging.getLogger(__name__)


def _run_once(
    settings: Settings,
    factory: sessionmaker[Session],
) -> sandbox_service.ReaperStats:
    with factory() as session:
        stats = sandbox_service.reap_sandboxes(
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


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="AGS 沙箱回收任务")
    parser.add_argument("--once", action="store_true", help="执行一轮后退出（供 cron 使用）")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    factory = create_session_factory(create_db_engine(settings.db.database_url))
    interval = settings.ags.sandbox_reaper_interval_seconds
    if args.once:
        _run_once(settings, factory)
        return 0

    while True:
        try:
            _run_once(settings, factory)
        except Exception:
            logger.exception("sandbox reaper 执行失败")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
