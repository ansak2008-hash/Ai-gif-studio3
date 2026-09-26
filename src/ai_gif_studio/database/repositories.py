from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission

from .tables import ProcessingJobRecord


class JobRepository(Protocol):
    async def create(self, submission: VideoSubmission) -> ProcessingJob: ...

    async def get(self, job_id: UUID) -> ProcessingJob | None: ...


class SqlAlchemyJobRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, submission: VideoSubmission) -> ProcessingJob:
        job = ProcessingJob(
            id=uuid4(),
            status=JobStatus.RECEIVED,
            submission=submission,
            created_at=datetime.now(UTC),
        )
        record = ProcessingJobRecord(
            id=str(job.id),
            status=job.status.value,
            telegram_file_id=submission.telegram_file_id,
            original_filename=submission.original_filename,
            content_type=submission.content_type,
            file_size_bytes=submission.file_size_bytes,
            submitted_by=submission.submitted_by,
            mode=submission.mode.value,
            created_at=job.created_at,
        )
        async with self._session_factory() as session:
            session.add(record)
            await session.commit()
        return job

    async def get(self, job_id: UUID) -> ProcessingJob | None:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(ProcessingJobRecord).where(ProcessingJobRecord.id == str(job_id))
            )
        if record is None:
            return None
        return ProcessingJob(
            id=UUID(record.id),
            status=JobStatus(record.status),
            created_at=record.created_at,
            submission=VideoSubmission(
                telegram_file_id=record.telegram_file_id,
                original_filename=record.original_filename,
                content_type=record.content_type,
                file_size_bytes=record.file_size_bytes,
                submitted_by=record.submitted_by,
                mode=ProcessingMode(record.mode),
            ),
        )
