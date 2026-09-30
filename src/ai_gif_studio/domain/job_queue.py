from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from ai_gif_studio.models import JobStatus, ProcessingJob


class JobQueueRepository(Protocol):
    async def get(self, job_id: UUID) -> ProcessingJob | None: ...
    async def set_status(
        self,
        job_id: UUID,
        status: str,
        expected_status: str | None = None,
    ) -> bool: ...


class DuplicateEnqueueError(RuntimeError):
    """The job is already queued or has progressed beyond the enqueue boundary."""


class LostClaimError(RuntimeError):
    """Another worker won the atomic queued-to-processing transition."""


class AtomicJobQueue:
    """Persistent CAS-based queue boundary; no process-local state is used."""

    def __init__(self, repository: JobQueueRepository) -> None:
        self._repository = repository

    async def enqueue(self, job: ProcessingJob) -> ProcessingJob | None:
        changed = await self._repository.set_status(
            job.id,
            JobStatus.QUEUED.value,
            expected_status=JobStatus.CREATED.value,
        )
        if not changed:
            current = await self._repository.get(job.id)
            if current is not None and current.status in {
                JobStatus.QUEUED,
                JobStatus.PROCESSING,
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            }:
                return None
            raise DuplicateEnqueueError(f"job {job.id} could not be enqueued atomically")
        return await self._repository.get(job.id)

    async def claim_for_processing(self, job_id: UUID, worker_id: str) -> ProcessingJob | None:
        if not isinstance(worker_id, str) or not worker_id:
            raise ValueError("worker_id must be a non-empty string")
        changed = await self._repository.set_status(
            job_id,
            JobStatus.PROCESSING.value,
            expected_status=JobStatus.QUEUED.value,
        )
        if not changed:
            return None
        return await self._repository.get(job_id)

    async def complete(self, job_id: UUID) -> None:
        changed = await self._repository.set_status(
            job_id,
            JobStatus.COMPLETED.value,
            expected_status=JobStatus.PROCESSING.value,
        )
        if not changed:
            raise LostClaimError(f"job {job_id} no longer belongs to the processing worker")

    async def fail(self, job_id: UUID, error: str) -> None:
        if not isinstance(error, str):
            raise TypeError("error must be a string")
        changed = await self._repository.set_status(
            job_id,
            JobStatus.FAILED.value,
            expected_status=JobStatus.PROCESSING.value,
        )
        if not changed:
            raise LostClaimError(f"job {job_id} no longer belongs to the processing worker")

    async def enqueue_job(self, job_id: str, **_: object) -> ProcessingJob | None:
        parsed = UUID(job_id)
        job = await self._repository.get(parsed)
        if job is None:
            raise KeyError(f"job not found: {job_id}")
        return await self.enqueue(job)
