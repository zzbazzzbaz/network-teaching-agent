from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from app.core.config import Settings
from app.models.user_sandbox import SandboxStatus, UserSandbox


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    timeout_seconds: int
    idle_seconds: int
    paused_retention_seconds: int
    max_lifetime_seconds: int
    heartbeat_seconds: int

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        ags = settings.ags
        return cls(
            timeout_seconds=ags.sandbox_timeout_seconds,
            idle_seconds=ags.sandbox_idle_seconds,
            paused_retention_seconds=ags.sandbox_paused_retention_seconds,
            max_lifetime_seconds=ags.sandbox_max_lifetime_seconds,
            heartbeat_seconds=ags.sandbox_heartbeat_seconds,
        )

    def expires_at(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self.timeout_seconds)

    def hard_destroy_at(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self.max_lifetime_seconds)

    def idle_before(self, now: datetime) -> datetime:
        return now - timedelta(seconds=self.idle_seconds)

    def paused_before(self, now: datetime) -> datetime:
        return now - timedelta(seconds=self.paused_retention_seconds)

    def is_over_lifetime(self, record: UserSandbox, now: datetime) -> bool:
        return record.hard_destroy_at <= now

    def is_paused_expired(self, record: UserSandbox, now: datetime) -> bool:
        return (
            record.state is SandboxStatus.PAUSED
            and record.paused_at is not None
            and record.paused_at <= self.paused_before(now)
        )

    def needs_rotation(self, record: UserSandbox, now: datetime) -> bool:
        return self.is_over_lifetime(record, now) or self.is_paused_expired(record, now)
