from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from ai_gif_studio.models import ProcessingJob


class JobQueueError(RuntimeError):
    """Base error for queue ownership and state failures."""


class DuplicateEnqueueError(JobQueueError):
    """The job is already beyond the CREATED enqueue boundary."""


class LostClaimError(JobQueueError):
    """The caller no longer owns the processing claim."""


class LeaseExpiredError(JobQueueError):
    """The processing lease is no longer valid."""


class TransportSendError(JobQueueError):
    """The durable queue transition succeeded but transport dispatch failed."""


@dataclass(frozen=True, slots=True)
class QueueConfig:
    lease_duration_seconds: int = 600
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.lease_duration_seconds <= 0:
            raise ValueError("lease_duration_seconds must be positive")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")


@dataclass(frozen=True, slots=True)
class ClaimResult:
    job: ProcessingJob
    owner_id: str
    attempt: int
    lease_expires_at: datetime
    version: int


class JobQueueRepository(Protocol):
    async def get(self, job_id: UUID) -> ProcessingJob | None: ...

    async def transition_created_to_queued(self, job_id: UUID) -> bool: ...

    async def rollback_queued_to_created(self, job_id: UUID) -> bool: ...

    async def claim_for_processing(
        self, job_id: UUID, owner_id: str, lease_expires_at: datetime
    ) -> ClaimResult | None: ...

    async def complete_processing(
        self, job_id: UUID, owner_id: str, version: int, now: datetime
    ) -> bool: ...

    async def fail_processing(
        self, job_id: UUID, owner_id: str, version: int, error: str, now: datetime
    ) -> bool: ...

    async def retry_processing(
        self, job_id: UUID, owner_id: str, version: int, error: str, now: datetime
    ) -> bool: ...

    async def recover_expired_processing(self, now: datetime, max_attempts: int) -> list[UUID]: ...


class JobDispatcher(Protocol):
    async def __call__(self, job_id: str, **kwargs: object) -> object: ...


class AtomicJobQueue:
    """Single state authority with CAS, ownership fencing and lease recovery."""

    def __init__(
        self,
        repository: JobQueueRepository,
        dispatcher: JobDispatcher | None = None,
        config: QueueConfig | None = None,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher
        self._config = config or QueueConfig()

    async def enqueue(self, job: ProcessingJob) -> ProcessingJob | None:
        current = await self._repository.get(job.id)
        if current is None:
            raise KeyError(f"job not found: {job.id}")
        if current.status.value != "created":
            return None
        if not await self._repository.transition_created_to_queued(job.id):
            return None
        if self._dispatcher is not None:
            try:
                await self._dispatcher(str(job.id))
            except Exception as exc:
                rolled_back = await self._repository.rollback_queued_to_created(job.id)
                if not rolled_back:
                    raise TransportSendError(
                        f"dispatch failed and job {job.id} could not be rolled back"
                    ) from exc
                raise TransportSendError(f"dispatch failed for job {job.id}") from exc
        return await self._repository.get(job.id)

    async def claim_for_processing(self, job_id: UUID, worker_id: str) -> ClaimResult | None:
        self._validate_owner(worker_id)
        now = datetime.now(UTC)
        lease = now + timedelta(seconds=self._config.lease_duration_seconds)
        return await self._repository.claim_for_processing(job_id, worker_id, lease)

    async def complete(self, job_id: UUID, worker_id: str, version: int) -> None:
        self._validate_owner(worker_id)
        if not await self._repository.complete_processing(
            job_id, worker_id, version, datetime.now(UTC)
        ):
            raise LostClaimError(f"job {job_id} is not owned by {worker_id}")

    async def fail(self, job_id: UUID, worker_id: str, version: int, error: str) -> None:
        self._validate_owner(worker_id)
        if not isinstance(error, str):
            raise TypeError("error must be a string")
        if not await self._repository.fail_processing(
            job_id, worker_id, version, error, datetime.now(UTC)
        ):
            raise LostClaimError(f"job {job_id} is not owned by {worker_id}")

    async def retry(self, job_id: UUID, worker_id: str, version: int, error: str) -> bool:
        self._validate_owner(worker_id)
        if not isinstance(error, str):
            raise TypeError("error must be a string")
        return await self._repository.retry_processing(
            job_id, worker_id, version, error, datetime.now(UTC)
        )

    async def recover_expired(self) -> int:
        recovered = await self._repository.recover_expired_processing(
            datetime.now(UTC), self._config.max_attempts
        )
        if self._dispatcher is None:
            return len(recovered)
        dispatched = 0
        for job_id in recovered:
            try:
                await self._dispatcher(str(job_id))
            except Exception as exc:
                raise TransportSendError(f"recovered job {job_id} could not be dispatched") from exc
            dispatched += 1
        return dispatched

    async def enqueue_job(self, job_id: str, **_: object) -> ProcessingJob | None:
        return await self.enqueue(await self._require_job(UUID(job_id)))

    async def _require_job(self, job_id: UUID) -> ProcessingJob:
        job = await self._repository.get(job_id)
        if job is None:
            raise KeyError(f"job not found: {job_id}")
        return job

    @staticmethod
    def _validate_owner(owner_id: str) -> None:
        if not isinstance(owner_id, str) or not owner_id:
            raise ValueError("owner_id must be a non-empty string")
