from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ai_gif_studio.database.repositories import SqlAlchemyDeliveryLog
from ai_gif_studio.database.tables import ArtifactRecord, Base, ProcessingJobRecord
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
    unknown = next_state_on_reobserve(DeliveryRecord(identity(), DeliveryState.INTENT, 1))
    with pytest.raises(ValueError):
        mark_failed(unknown, "late")


def test_crash_window_never_resends() -> None:
    rec = DeliveryRecord(identity(), DeliveryState.INTENT, 1)
    assert decide_send(rec, DeliveryConfig()) is SendDecision.HOLD_UNKNOWN
    assert next_state_on_reobserve(rec).state is DeliveryState.UNKNOWN


def test_unknown_reobserve_is_terminal_without_new_send() -> None:
    rec = DeliveryRecord(
        identity(),
        DeliveryState.UNKNOWN,
        1,
        error="prior send outcome unknowable; manual resolution required",
    )
    assert decide_send(rec, DeliveryConfig()) is SendDecision.HOLD_UNKNOWN
    assert next_state_on_reobserve(rec) == rec


@pytest.mark.asyncio
async def test_cancellation_not_swallowed_by_a2_boundary() -> None:
    async def deliver_with_cancellation() -> None:
        try:
            await asyncio.sleep(0)
            raise asyncio.CancelledError
        except Exception as error:
            pytest.fail(f"CancelledError was swallowed: {error}")

    with pytest.raises(asyncio.CancelledError):
        await deliver_with_cancellation()


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
    assert (
        select_redispatch_candidates(
            [QueuedSnapshot(uuid4(), "queued", now)],
            now,
            timedelta(seconds=10),
            50,
        )
        == []
    )


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
    report = await RecoveryScheduler(
        repository, dispatch, lock
    ).run_once(datetime.now(UTC))

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


@pytest.mark.asyncio
async def test_delivery_log_atomic_identity(tmp_path) -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'delivery.db'}"
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    job_id, artifact_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add(
            ProcessingJobRecord(
                id=str(job_id),
                status="queued",
                telegram_file_id="file",
                file_size_bytes=1,
                submitted_by=1,
                mode="crop_only",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ArtifactRecord(
                artifact_id=str(artifact_id),
                job_id=str(job_id),
                type="output_gif",
                storage_path="/tmp/output.gif",
                mime_type="image/gif",
                size_bytes=1,
                sha256="0" * 64,
                created_at=now,
            )
        )
        await session.commit()

    log = SqlAlchemyDeliveryLog(session_factory)
    delivery_identity = DeliveryIdentity(job_id, artifact_id, "telegram")
    first, second = await asyncio.gather(
        log.begin_delivery(delivery_identity),
        log.begin_delivery(delivery_identity),
    )

    assert first == second
    assert first.state is DeliveryState.INTENT
    assert first.attempt == 1
    await engine.dispose()
