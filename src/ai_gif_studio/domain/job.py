from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class JobStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class JobStep:
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    retry_count: int = 0
    error: str | None = None


@dataclass(slots=True)
class Job:
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: list[JobStep] = field(default_factory=list)
    error: str | None = None

    def transition(self, status: JobStatus):
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
