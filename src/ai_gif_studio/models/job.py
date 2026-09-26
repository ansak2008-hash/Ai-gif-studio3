from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ProcessingMode(StrEnum):
    DESIGNED = "designed"
    CROP_ONLY = "crop_only"


class JobStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.CREATED: frozenset({JobStatus.QUEUED, JobStatus.CANCELLED}),
    JobStatus.QUEUED: frozenset({JobStatus.PROCESSING, JobStatus.CANCELLED}),
    JobStatus.PROCESSING: frozenset(
        {JobStatus.QUEUED, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


@dataclass(frozen=True, slots=True)
class VideoSubmission:
    telegram_file_id: str
    original_filename: str | None
    content_type: str | None
    file_size_bytes: int
    submitted_by: int
    mode: ProcessingMode = ProcessingMode.CROP_ONLY
    source_message_id: int | None = None


@dataclass(frozen=True, slots=True)
class ProcessingJob:
    id: UUID
    status: JobStatus
    submission: VideoSubmission
    created_at: datetime
