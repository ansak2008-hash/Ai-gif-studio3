from __future__ import annotations

import hashlib
from mimetypes import guess_type
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission

from .tables import ArtifactRecord, JobStepRecord, ProcessingJobRecord


class JobRepository(Protocol):
    async def create(self, submission: VideoSubmission) -> ProcessingJob: ...
    async def get(self, job_id: UUID) -> ProcessingJob | None: ...
    async def count_active(self) -> int: ...


class SqlAlchemyJobRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, submission: VideoSubmission) -> ProcessingJob:
        job = ProcessingJob(
            id=uuid4(),
            status=JobStatus.CREATED,
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
                record.telegram_file_id,
                record.original_filename,
                record.content_type,
                record.file_size_bytes,
                record.submitted_by,
                ProcessingMode(record.mode),
            ),
        )

    async def count_active(self) -> int:
        async with self._session_factory() as session:
            result = await session.scalar(
                select(func.count())
                .select_from(ProcessingJobRecord)
                .where(
                    ProcessingJobRecord.status.in_(
                        (JobStatus.CREATED.value, JobStatus.QUEUED.value, JobStatus.PROCESSING.value)
                    )
                )
            )
        return int(result or 0)

    async def set_status(
        self, job_id: UUID, status: str, expected_status: str | None = None
    ) -> bool:
        async with self._session_factory() as session:
            statement = update(ProcessingJobRecord).where(ProcessingJobRecord.id == str(job_id))
            if expected_status is not None:
                statement = statement.where(ProcessingJobRecord.status == expected_status)
            result = await session.execute(statement.values(status=status))
            await session.commit()
        return result.rowcount == 1


class JobStepRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def start(self, job_id: UUID, name: str) -> UUID:
        step_id = uuid4()
        async with self._session_factory() as session:
            session.add(
                JobStepRecord(
                    id=str(step_id),
                    job_id=str(job_id),
                    name=name,
                    status="running",
                    started_at=datetime.now(UTC),
                    retry_count=0,
                )
            )
            await session.commit()
        return step_id

    async def complete(self, step_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(JobStepRecord).where(JobStepRecord.id == str(step_id)))
            if row is None:
                raise RuntimeError(f"job step {step_id} not found")
            now = datetime.now(UTC)
            row.status = "completed"
            row.completed_at = now
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
            await session.commit()

    async def fail(self, step_id: UUID, error: str, retry_count: int = 0) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(JobStepRecord).where(JobStepRecord.id == str(step_id)))
            if row is None:
                raise RuntimeError(f"job step {step_id} not found")
            now = datetime.now(UTC)
            row.status = "failed"
            row.completed_at = now
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
            row.retry_count = retry_count
            row.error = error[-4000:]
            await session.commit()


class ArtifactRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def register(self, job_id: UUID, path: Path, artifact_type: str, mime_type: str):
        if not path.is_file():
            raise FileNotFoundError(path)
        if not path.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError("invalid artifact path")
        detected_mime = guess_type(path.name)[0]
        if detected_mime and detected_mime != mime_type:
            raise ValueError(f"artifact MIME mismatch: expected {mime_type}, detected {detected_mime}")
        h = hashlib.sha256()
        size = 0
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
                size += len(chunk)
        row = ArtifactRecord(
            artifact_id=str(uuid4()),
            job_id=str(job_id),
            type=artifact_type,
            storage_path=str(path),
            mime_type=mime_type,
            size_bytes=size,
            sha256=h.hexdigest(),
            created_at=datetime.now(UTC),
            metadata={},
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return row
