from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ProcessingMode(StrEnum):
    DESIGNED = "designed"
    CROP_ONLY = "crop_only"


class JobStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class VideoSubmission:
    telegram_file_id: str
    original_filename: str | None
    content_type: str | None
    file_size_bytes: int
    submitted_by: int
    mode: ProcessingMode = ProcessingMode.DESIGNED


@dataclass(frozen=True, slots=True)
class ProcessingJob:
    id: UUID
    status: JobStatus
    submission: VideoSubmission
    created_at: datetime
