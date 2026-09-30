from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.job_queue import (
    AtomicJobQueue,
    LostClaimError,
    QueueConfig,
    TransportSendError,
)
from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission

pytestmark = pytest.mark.unit


class FakeRepository:
    def __init__(self, job: ProcessingJob) -> None:
        self.job = job
        self.version = 0
        self.attempt = 0
        self.owner_id: str | None = None
        self.lease_expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get(self, job_id: UUID) -> ProcessingJob | None:
        return self.job if job_id == self.job.id else None

    async def transition_created_to_queued(self, job_id: UUID) -> bool:
        async with self._lock:
            if job_id != self.job.id or self.job.status is not JobStatus.CREATED:
                return False
            self.job = ProcessingJob(
                self.job.id, JobStatus.QUEUED, self.job.submission, self.job.created_at
            )
            self.version += 1
            return True

    async def rollback_queued_to_created(self, job_id: UUID) -> bool:
        async with self._lock:
            if job_id != self.job.id or self.job.status is not JobStatus.QUEUED:
                return False
            self.job = ProcessingJob(
                self.job.id, JobStatus.CREATED, self.job.submission, self.job.created_at
            )
            self.version += 1
            return True

    async def claim_for_processing(self, job_id: UUID, owner_id: str, lease_expires_at: datetime):
        async with self._lock:
            if job_id != self.job.id or self.job.status is not JobStatus.QUEUED:
                return None
            self.job = ProcessingJob(
                self.job.id, JobStatus.PROCESSING, self.job.submission, self.job.created_at
            )
            self.owner_id = owner_id
            self.lease_expires_at = lease_expires_at
            self.attempt += 1
            self.version += 1
            from ai_gif_studio.domain.job_queue import ClaimResult

            return ClaimResult(self.job, owner_id, self.attempt, lease_expires_at, self.version)

    async def complete_processing(self, job_id: UUID, owner_id: str, version: int, now: datetime) -> bool:
        async with self._lock:
            if not self._owns(job_id, owner_id, now):
                return False
            self.job = ProcessingJob(
                self.job.id, JobStatus.COMPLETED, self.job.submission, self.job.created_at
            )
            self.owner_id = None
            self.lease_expires_at = None
            self.version += 1
            return True

    async def fail_processing(self, job_id: UUID, owner_id: str, version: int, error: str, now: datetime) -> bool:
        async with self._lock:
            if not self._owns(job_id, owner_id, now):
                return False
            self.job = ProcessingJob(
                self.job.id, JobStatus.FAILED, self.job.submission, self.job.created_at
            )
            self.owner_id = None
            self.lease_expires_at = None
            self.version += 1
            return True

    async def retry_processing(
        self, job_id: UUID, owner_id: str, version: int, error: str, now: datetime
    ) -> bool:
        async with self._lock:
            if not self._owns(job_id, owner_id, now):
                return False
            self.job = ProcessingJob(
                self.job.id, JobStatus.QUEUED, self.job.submission, self.job.created_at
            )
            self.owner_id = None
            self.lease_expires_at = None
            self.version += 1
            return True

    async def recover_expired_processing(self, now: datetime, max_attempts: int) -> list[UUID]:
        async with self._lock:
            if (
                self.job.status is not JobStatus.PROCESSING
                or self.lease_expires_at is None
                or self.lease_expires_at > now
            ):
                return []
            self.owner_id = None
            self.lease_expires_at = None
            self.version += 1
            if self.attempt >= max_attempts:
                self.job = ProcessingJob(
                    self.job.id, JobStatus.FAILED, self.job.submission, self.job.created_at
                )
                return []
            self.job = ProcessingJob(
                self.job.id, JobStatus.QUEUED, self.job.submission, self.job.created_at
            )
            return [self.job.id]

    def _owns(self, job_id: UUID, owner_id: str, version: int, now: datetime) -> bool:
        return (
            job_id == self.job.id
            and self.job.status is JobStatus.PROCESSING
            and self.owner_id == owner_id
            and self.version == version
            and self.lease_expires_at is not None
            and self.lease_expires_at > now
        )


def make_job() -> ProcessingJob:
    return ProcessingJob(
        uuid4(),
        JobStatus.CREATED,
        VideoSubmission("file", "video.mp4", "video/mp4", 10, 123, ProcessingMode.CROP_ONLY),
        datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_enqueue_transitions_before_dispatch() -> None:
    repo = FakeRepository(make_job())
    observed: list[JobStatus] = []

    async def dispatch(_job_id: str, **_: object) -> None:
        observed.append(repo.job.status)

    queue = AtomicJobQueue(repo, dispatch)
    assert await queue.enqueue(repo.job) is not None
    assert observed == [JobStatus.QUEUED]


@pytest.mark.asyncio
async def test_dispatch_failure_rolls_back_created() -> None:
    repo = FakeRepository(make_job())

    async def dispatch(_job_id: str, **_: object) -> None:
        raise RuntimeError("redis unavailable")

    queue = AtomicJobQueue(repo, dispatch)
    with pytest.raises(TransportSendError):
        await queue.enqueue(repo.job)
    assert repo.job.status is JobStatus.CREATED


@pytest.mark.asyncio
async def test_enqueue_race_has_one_winner() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    start = asyncio.Event()

    async def call() -> ProcessingJob | None:
        await start.wait()
        return await queue.enqueue(repo.job)

    calls = [asyncio.create_task(call()) for _ in range(32)]
    start.set()
    results = await asyncio.gather(*calls)
    assert sum(result is not None for result in results) == 1
    assert repo.job.status is JobStatus.QUEUED


@pytest.mark.asyncio
async def test_claim_race_has_one_owner() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    barrier = asyncio.Barrier(32)

    async def claim(worker: int):
        await barrier.wait()
        return await queue.claim_for_processing(repo.job.id, f"worker-{worker}")

    results = await asyncio.gather(*(claim(i) for i in range(32)))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert winners[0].owner_id.startswith("worker-")


@pytest.mark.asyncio
async def test_only_current_owner_can_complete_or_fail() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    await queue.claim_for_processing(repo.job.id, "owner-a")
    with pytest.raises(LostClaimError):
        await queue.complete(repo.job.id, "owner-b", claim.version)
    await queue.complete(repo.job.id, "owner-a", claim.version)
    assert repo.job.status is JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_retry_is_queue_authority_and_increments_on_next_claim() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    first = await queue.claim_for_processing(repo.job.id, "owner-a")
    assert first is not None and first.attempt == 1
    assert first is not None
    assert await queue.retry(repo.job.id, "owner-a", first.version, "temporary failure")
    assert repo.job.status is JobStatus.QUEUED
    second = await queue.claim_for_processing(repo.job.id, "owner-b")
    assert second is not None and second.attempt == 2


@pytest.mark.asyncio
async def test_expired_owner_is_fenced_and_recovered() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo, config=QueueConfig(lease_duration_seconds=1, max_attempts=3))
    await queue.enqueue(repo.job)
    claim = await queue.claim_for_processing(repo.job.id, "stale")
    assert claim is not None
    repo.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    recovered: list[str] = []

    async def dispatch(job_id: str, **_: object) -> None:
        recovered.append(job_id)

    recovery_queue = AtomicJobQueue(repo, dispatch, QueueConfig(max_attempts=3))
    assert await recovery_queue.recover_expired() == 1
    assert recovered == [str(repo.job.id)]
    with pytest.raises(LostClaimError):
        await recovery_queue.complete(repo.job.id, "stale", claim.version)


@pytest.mark.asyncio
async def test_expired_attempt_limit_fails_closed() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo, config=QueueConfig(max_attempts=1))
    await queue.enqueue(repo.job)
    assert await queue.claim_for_processing(repo.job.id, "worker") is not None
    repo.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert await queue.recover_expired() == 0
    assert repo.job.status is JobStatus.FAILED


@pytest.mark.asyncio
async def test_invalid_owner_is_rejected() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    with pytest.raises(ValueError):
        await queue.claim_for_processing(repo.job.id, "")


@pytest.mark.asyncio
async def test_stale_version_is_fenced_even_when_owner_id_is_reused() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo, config=QueueConfig(lease_duration_seconds=1, max_attempts=3))
    await queue.enqueue(repo.job)
    first = await queue.claim_for_processing(repo.job.id, "worker")
    assert first is not None
    repo.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert await queue.recover_expired() == 1
    second = await queue.claim_for_processing(repo.job.id, "worker")
    assert second is not None
    assert second.version != first.version
    with pytest.raises(LostClaimError):
        await queue.complete(repo.job.id, "worker", first.version)
    await queue.complete(repo.job.id, "worker", second.version)
    assert repo.job.status is JobStatus.COMPLETED
