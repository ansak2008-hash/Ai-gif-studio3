from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RecoveryConfig:
    interval: timedelta = timedelta(seconds=30)
    redispatch_grace: timedelta = timedelta(seconds=10)
    batch_size: int = 50
    max_consecutive_dispatch_failures: int = 5

    def __post_init__(self) -> None:
        if self.interval <= timedelta(0):
            raise ValueError("interval must be positive")
        if self.redispatch_grace < timedelta(0):
            raise ValueError("redispatch_grace must be non-negative")
        if self.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if self.max_consecutive_dispatch_failures < 1:
            raise ValueError("max_consecutive_dispatch_failures must be >= 1")


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    recovered_to_queued: int
    redispatched: int
    dispatch_failures: int
    lock_acquired: bool


@dataclass(frozen=True, slots=True)
class QueuedSnapshot:
    job_id: UUID
    status: str
    updated_at: datetime


def select_redispatch_candidates(
    snapshots: list[QueuedSnapshot],
    now: datetime,
    grace: timedelta,
    limit: int,
) -> list[UUID]:
    if limit < 1:
        return []
    cutoff = now - grace
    picked = sorted(
        (
            snapshot
            for snapshot in snapshots
            if snapshot.status == "queued" and snapshot.updated_at <= cutoff
        ),
        key=lambda snapshot: (snapshot.updated_at, snapshot.job_id.hex),
    )
    return [snapshot.job_id for snapshot in picked[:limit]]


class RecoveryDispatchError(RuntimeError):
    """The durable job remains QUEUED because transport dispatch failed."""


class RecoveryLockPort(Protocol):
    async def try_acquire(self, ttl: timedelta) -> str | None: ...

    async def release(self, token: str) -> None: ...


class RecoverySchedulerPort(Protocol):
    async def run_once(self, now: datetime) -> RecoveryReport: ...


RECOVERY_INVARIANTS = {
    "no_orphan_queued": "Stale QUEUED jobs are selected on repeated scans until dispatch succeeds.",
    "dispatch_failure_never_fails_job": "Recovery dispatch failure leaves the job QUEUED.",
    "single_flight_reaper": "Only the holder of the distributed lease executes a recovery cycle.",
    "duplicate_dispatch_is_safe": "Duplicate triggers are harmless because claim_for_processing is the execution CAS.",
}
