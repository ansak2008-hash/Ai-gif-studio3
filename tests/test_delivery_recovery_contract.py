from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ai_gif_studio.domain.delivery_contract import (
    DeliveryConfig,
    DeliveryIdentity,
    DeliveryRecord,
    DeliveryState,
    SendDecision,
    begin_retry,
    decide_send,
    mark_failed,
    mark_sent,
    next_state_on_reobserve,
)
from ai_gif_studio.domain.recovery_contract import (
    QueuedSnapshot,
    RecoveryDispatchError,
    select_redispatch_candidates,
)
from ai_gif_studio.infrastructure.recovery import RecoveryScheduler

pytestmark = pytest.mark.unit


def identity() -> DeliveryIdentity:
    return DeliveryIdentity(uuid4(), uuid4(), "telegram")


def test_bounded_retry() -> None:
    cfg = DeliveryConfig(max_attempts=3)
    rec = DeliveryRecord(identity(), DeliveryState.FAILED, 1, error="network")
    assert decide_send(rec, cfg) is SendDecision.RETRY
    retry = begin_retry(rec, cfg)
    assert retry is not None and retry.attempt == 2


def test_retry_exhaustion() -> None:
    cfg = DeliveryConfig(max_attempts=3)
    rec = DeliveryRecord(identity(), DeliveryState.FAILED, 3, error="network")
    assert decide_send(rec, cfg) is SendDecision.GIVE_UP
    assert begin_retry(rec, cfg) is None


def test_terminal_states_are_immutable() -> None:
    rec = DeliveryRecord(identity(), DeliveryState.SENT, 1, external_ref="msg-1")
    with pytest.raises(ValueError):
        mark_sent(rec, "msg-2")
    unknown = next_state_on_reobserve(
        DeliveryRecord(identity(), DeliveryState.INTENT, 1)
    )
    with pytest.raises(ValueError):
        mark_failed(unknown, "late")


def test_crash_window_never_resends() -> None:
    rec = DeliveryRecord(identity(), DeliveryState.INTENT, 1)
    assert decide_send(rec, DeliveryConfig()) is SendDecision.HOLD_UNKNOWN
    assert next_state_on_reobserve(rec).state is DeliveryState.UNKNOWN


def test_state_fields_are_enforced() -> None:
    with pytest.raises(ValueError):
        DeliveryRecord(identity(), DeliveryState.INTENT, 0)
    with pytest.raises(ValueError):
        DeliveryRecord(identity(), DeliveryState.SENT, 1)
    with pytest.raises(ValueError):
        DeliveryRecord(identity(), DeliveryState.FAILED, 1)


def test_deterministic_redispatch_selection() -> None:
    now = datetime.now(UTC)
    stale = now - timedelta(minutes=1)
    first, second = uuid4(), uuid4()
    snapshots = [
        QueuedSnapshot(second, "queued", stale),
        QueuedSnapshot(first, "queued", stale),
    ]
    assert select_redispatch_candidates(snapshots, now, timedelta(seconds=10), 1) == [
        min(first, second, key=lambda value: value.hex)
    ]


def test_fresh_queued_job_is_not_selected() -> None:
    now = datetime.now(UTC)
    assert select_redispatch_candidates(
        [QueuedSnapshot(uuid4(), "queued", now)],
        now,
        timedelta(seconds=10),
        50,
    ) == []


class FakeRecoveryRepository:
    def __init__(self, stale_ids):
        self.stale_ids = stale_ids
        self.recovered = []

    async def recover_expired_processing(self, now, max_attempts):
        return self.recovered

    async def get_stale_queued(self, cutoff, limit):
        return [(job_id, cutoff - timedelta(seconds=1)) for job_id in self.stale_ids[:limit]]


class FakeLock:
    def __init__(self, token="lock-token"):
        self.token = token
        self.acquired = 0
        self.released = 0
        self.held = False

    async def try_acquire(self, ttl):
        self.acquired += 1
        if self.held:
            return None
        self.held = True
        return self.token

    async def release(self, token):
        assert token == self.token
        self.released += 1
        self.held = False


@pytest.mark.asyncio
async def test_recovery_dispatch_failure_keeps_cycle_recoverable() -> None:
    job_id = uuid4()
    repository = FakeRecoveryRepository([job_id])

    async def dispatch(_job_id: str):
        raise RecoveryDispatchError("redis unavailable")

    lock = FakeLock()
    report = await RecoveryScheduler(repository, dispatch, lock).run_once(datetime.now(UTC))

    assert report.lock_acquired is True
    assert report.redispatched == 0
    assert report.dispatch_failures == 1
    assert lock.released == 1


@pytest.mark.asyncio
async def test_recovery_lock_skips_when_another_cycle_holds_it() -> None:
    repository = FakeRecoveryRepository([uuid4()])
    lock = FakeLock()
    lock.held = True

    async def dispatch(_value: str):
        raise AssertionError("dispatcher must not run without the lock")

    report = await RecoveryScheduler(repository, dispatch, lock).run_once(datetime.now(UTC))

    assert report.lock_acquired is False
    assert report.redispatched == 0
    assert lock.released == 0


@pytest.mark.asyncio
async def test_repeated_scan_retries_stale_queued_job() -> None:
    job_id = uuid4()
    repository = FakeRecoveryRepository([job_id])
    lock = FakeLock()
    attempts = 0

    async def dispatch(_job_id: str):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RecoveryDispatchError("temporary redis outage")

    scheduler = RecoveryScheduler(repository, dispatch, lock)
    first = await scheduler.run_once(datetime.now(UTC))
    second = await scheduler.run_once(datetime.now(UTC))

    assert first.dispatch_failures == 1
    assert second.redispatched == 1
    assert attempts == 2
