"""沙箱生命周期回收任务。

开发阶段手动执行：

    cd apps/api
    uv run python -m app.job.sandbox_reaper

生产环境由宿主机 cron 每 5 分钟执行一次。
"""

import logging

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import create_db_engine, create_session_factory
from app.services import sandbox_service

logger = logging.getLogger(__name__)


def run_reaper(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> sandbox_service.ReaperStats:
    with session_factory() as session:
        return sandbox_service.reap_sandboxes(
            session=session,
            settings=settings,
        )


def _run_once(settings: Settings, engine: Engine) -> int:
    session_factory = create_session_factory(engine)
    stats = run_reaper(settings=settings, session_factory=session_factory)
    logger.info(
        "sandbox reaper: paused=%s destroyed=%s cleared=%s failed=%s",
        stats.paused,
        stats.destroyed,
        stats.cleared,
        stats.failed,
    )
    return 1 if stats.failed else 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()
    engine = create_db_engine(settings.db.database_url)
    try:
        return _run_once(settings, engine)
    except Exception:
        logger.exception("sandbox reaper 执行失败")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
