from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.job_queue import AtomicJobQueue, LostClaimError
from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission

pytestmark = pytest.mark.unit


class FakeRepository:
    def __init__(self, job: ProcessingJob) -> None:
        self.job = job
        self._lock = asyncio.Lock()

    async def get(self, job_id: UUID) -> ProcessingJob | None:
        if job_id != self.job.id:
            return None
        return self.job

    async def set_status(
        self, job_id: UUID, status: str, expected_status: str | None = None
    ) -> bool:
        async with self._lock:
            if job_id != self.job.id:
                return False
            current = self.job.status
            if expected_status is not None and current.value != expected_status:
                return False
            if current.value == status:
                return True
            if current is JobStatus.CREATED and status == JobStatus.QUEUED.value:
                self.job = ProcessingJob(
                    self.job.id, JobStatus.QUEUED, self.job.submission, self.job.created_at
                )
                return True
            if current is JobStatus.QUEUED and status == JobStatus.PROCESSING.value:
                self.job = ProcessingJob(
                    self.job.id, JobStatus.PROCESSING, self.job.submission, self.job.created_at
                )
                return True
            if current is JobStatus.PROCESSING and status == JobStatus.COMPLETED.value:
                self.job = ProcessingJob(
                    self.job.id, JobStatus.COMPLETED, self.job.submission, self.job.created_at
                )
                return True
            if current is JobStatus.PROCESSING and status == JobStatus.FAILED.value:
                self.job = ProcessingJob(
                    self.job.id, JobStatus.FAILED, self.job.submission, self.job.created_at
                )
                return True
            raise ValueError(f"invalid transition {current.value} -> {status}")


def make_job() -> ProcessingJob:
    return ProcessingJob(
        uuid4(),
        JobStatus.CREATED,
        VideoSubmission("file", "video.mp4", "video/mp4", 10, 123, ProcessingMode.CROP_ONLY),
        datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_for_duplicate_submission() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    assert await queue.enqueue(repo.job) is not None
    assert await queue.enqueue(repo.job) is None
    assert repo.job.status is JobStatus.QUEUED


@pytest.mark.asyncio
async def test_progressed_job_does_not_reenter_transport_enqueue() -> None:
    repo = FakeRepository(make_job())
    calls: list[str] = []

    async def dispatch(job_id: str) -> None:
        calls.append(job_id)

    queue = AtomicJobQueue(repo, dispatch)
    await queue.enqueue(repo.job)
    calls.clear()
    assert await queue.enqueue(repo.job) is None
    assert calls == []


@pytest.mark.asyncio
async def test_duplicate_enqueue_never_regresses_queued_to_created() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    assert await queue.enqueue(repo.job) is None
    assert repo.job.status is JobStatus.QUEUED


@pytest.mark.asyncio
async def test_dispatch_observes_created_before_atomic_state_transition() -> None:
    repo = FakeRepository(make_job())
    observed: list[JobStatus] = []

    async def dispatch(_job_id: str, **_: object) -> None:
        observed.append(repo.job.status)

    queue = AtomicJobQueue(repo, dispatch)
    await queue.enqueue(repo.job)
    assert observed == [JobStatus.CREATED]


@pytest.mark.asyncio
async def test_dispatch_failure_leaves_created_state() -> None:
    repo = FakeRepository(make_job())

    async def dispatch(_job_id: str, **_: object) -> None:
        raise RuntimeError("redis unavailable")

    queue = AtomicJobQueue(repo, dispatch)
    with pytest.raises(RuntimeError):
        await queue.enqueue(repo.job)
    assert repo.job.status is JobStatus.CREATED


@pytest.mark.asyncio
async def test_claim_is_single_winner_under_concurrency() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    results = await asyncio.gather(
        *(queue.claim_for_processing(repo.job.id, f"worker-{i}") for i in range(32))
    )
    assert sum(result is not None for result in results) == 1
    assert repo.job.status is JobStatus.PROCESSING


@pytest.mark.asyncio
async def test_lost_claim_returns_none() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    assert await queue.claim_for_processing(repo.job.id, "winner") is not None
    assert await queue.claim_for_processing(repo.job.id, "loser") is None


@pytest.mark.asyncio
async def test_complete_requires_current_processing_claim() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    await queue.claim_for_processing(repo.job.id, "worker")
    await queue.complete(repo.job.id)
    assert repo.job.status is JobStatus.COMPLETED
    with pytest.raises(LostClaimError):
        await queue.complete(repo.job.id)


@pytest.mark.asyncio
async def test_fail_requires_current_processing_claim() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    await queue.claim_for_processing(repo.job.id, "worker")
    await queue.fail(repo.job.id, "failure")
    assert repo.job.status is JobStatus.FAILED
    with pytest.raises(LostClaimError):
        await queue.fail(repo.job.id, "late failure")


@pytest.mark.asyncio
async def test_enqueue_missing_job_fails_closed() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    with pytest.raises(KeyError):
        await queue.enqueue_job(str(uuid4()))


@pytest.mark.parametrize("worker_id", ["", 0, None])
@pytest.mark.asyncio
async def test_invalid_worker_id_is_rejected(worker_id: object) -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    with pytest.raises(ValueError):
        await queue.claim_for_processing(repo.job.id, worker_id)  # type: ignore[arg-type]


@pytest.mark.parametrize("attempt", range(16))
@pytest.mark.asyncio
async def test_repeated_duplicate_enqueue_never_changes_state(attempt: int) -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    await queue.enqueue(repo.job)
    for _ in range(attempt + 1):
        assert await queue.enqueue(repo.job) is None
        assert repo.job.status is JobStatus.QUEUED


@pytest.mark.asyncio
async def test_race_between_enqueue_callers_has_one_winner() -> None:
    repo = FakeRepository(make_job())
    queue = AtomicJobQueue(repo)
    results = await asyncio.gather(*(queue.enqueue(repo.job) for _ in range(32)))
    assert sum(result is not None for result in results) == 1
    assert repo.job.status is JobStatus.QUEUED
