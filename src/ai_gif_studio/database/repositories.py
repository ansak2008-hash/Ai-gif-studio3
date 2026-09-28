from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from mimetypes import guess_type
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.models import (
    JobStatus,
    ProcessingJob,
    ProcessingMode,
    VideoSubmission,
    can_transition,
)

from .tables import (
    ArtifactRecord,
    DesignSpecRecord,
    JobStepRecord,
    ProcessingJobRecord,
    ProcessingSettingsRecord,
)


class JobRepository(Protocol):
    async def create(self, submission: VideoSubmission) -> ProcessingJob: ...
    async def get(self, job_id: UUID) -> ProcessingJob | None: ...
    async def get_by_submission_key(self, submitted_by: int, source_message_id: int) -> ProcessingJob | None: ...
    async def count_active(self) -> int: ...
    async def set_status(self, job_id: UUID, status: str, expected_status: str | None = None) -> bool: ...
    async def get_design_spec(self, job_id: UUID) -> DesignSpec: ...
    async def save_design_spec(self, job_id: UUID, spec: DesignSpec) -> None: ...
    async def get_processing_settings(self, job_id: UUID) -> ProcessingSettings: ...
    async def save_processing_settings(self, job_id: UUID, settings: ProcessingSettings) -> None: ...


class SqlAlchemyJobRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, submission: VideoSubmission) -> ProcessingJob:
        job = ProcessingJob(id=uuid4(), status=JobStatus.CREATED, submission=submission, created_at=datetime.now(UTC))
        record = ProcessingJobRecord(
            id=str(job.id), status=job.status.value, telegram_file_id=submission.telegram_file_id,
            original_filename=submission.original_filename, content_type=submission.content_type,
            file_size_bytes=submission.file_size_bytes, submitted_by=submission.submitted_by,
            source_message_id=submission.source_message_id, mode=submission.mode.value,
            created_at=job.created_at,
        )
        spec, settings = DesignSpec(), ProcessingSettings()
        async with self._session_factory() as session:
            session.add(record)
            session.add(DesignSpecRecord(job_id=str(job.id), schema_version=spec.schema_version, document=spec.model_dump(mode="json")))
            session.add(ProcessingSettingsRecord(job_id=str(job.id), schema_version=settings.schema_version, document=settings.model_dump(mode="json")))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if submission.source_message_id is None:
                    raise
                existing = await session.scalar(
                    select(ProcessingJobRecord).where(
                        ProcessingJobRecord.submitted_by == submission.submitted_by,
                        ProcessingJobRecord.source_message_id == submission.source_message_id,
                    )
                )
                if existing is None:
                    raise
                return ProcessingJob(
                    id=UUID(existing.id), status=JobStatus(existing.status), created_at=existing.created_at,
                    submission=VideoSubmission(
                        existing.telegram_file_id, existing.original_filename, existing.content_type,
                        existing.file_size_bytes, existing.submitted_by, ProcessingMode(existing.mode),
                        existing.source_message_id,
                    ),
                )
        return job

    async def get(self, job_id: UUID) -> ProcessingJob | None:
        async with self._session_factory() as session:
            record = await session.scalar(select(ProcessingJobRecord).where(ProcessingJobRecord.id == str(job_id)))
        if record is None:
            return None
        return ProcessingJob(
            id=UUID(record.id), status=JobStatus(record.status), created_at=record.created_at,
            submission=VideoSubmission(
                record.telegram_file_id, record.original_filename, record.content_type,
                record.file_size_bytes, record.submitted_by, ProcessingMode(record.mode), record.source_message_id,
            ),
        )

    async def get_by_submission_key(self, submitted_by: int, source_message_id: int) -> ProcessingJob | None:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(ProcessingJobRecord).where(
                    ProcessingJobRecord.submitted_by == submitted_by,
                    ProcessingJobRecord.source_message_id == source_message_id,
                )
            )
        if record is None:
            return None
        return ProcessingJob(
            id=UUID(record.id), status=JobStatus(record.status), created_at=record.created_at,
            submission=VideoSubmission(
                record.telegram_file_id, record.original_filename, record.content_type,
                record.file_size_bytes, record.submitted_by, ProcessingMode(record.mode),
                record.source_message_id,
            ),
        )

    async def count_active(self) -> int:
        async with self._session_factory() as session:
            result = await session.scalar(
                select(func.count()).select_from(ProcessingJobRecord).where(
                    ProcessingJobRecord.status.in_(
                        (JobStatus.CREATED.value, JobStatus.QUEUED.value, JobStatus.PROCESSING.value)
                    )
                )
            )
        return int(result or 0)

    async def set_status(self, job_id: UUID, status: str, expected_status: str | None = None) -> bool:
        target = JobStatus(status)
        async with self._session_factory() as session:
            current = await session.scalar(
                select(ProcessingJobRecord.status).where(ProcessingJobRecord.id == str(job_id))
            )
            if current is None:
                return False
            if expected_status is not None and current != expected_status:
                return False
            if current == target.value:
                return True
            if not can_transition(JobStatus(current), target):
                raise ValueError(f"invalid job transition: {current} -> {target.value}")
            result = await session.execute(
                update(ProcessingJobRecord)
                .where(
                    ProcessingJobRecord.id == str(job_id),
                    ProcessingJobRecord.status == current,
                )
                .values(status=target.value)
            )
            await session.commit()
        return result.rowcount == 1

    async def recover_stale_processing(
        self,
        cutoff: datetime,
        max_retries: int = 2,
    ) -> int:
        recovered = 0
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(JobStepRecord)
                    .join(ProcessingJobRecord, JobStepRecord.job_id == ProcessingJobRecord.id)
                    .where(
                        ProcessingJobRecord.status == JobStatus.PROCESSING.value,
                        JobStepRecord.status == "running",
                        JobStepRecord.started_at.is_not(None),
                        JobStepRecord.started_at <= cutoff,
                    )
                    .order_by(JobStepRecord.started_at.asc())
                )
            ).all()
            for step in rows:
                if step.retry_count >= max_retries:
                    await session.execute(
                        update(ProcessingJobRecord)
                        .where(
                            ProcessingJobRecord.id == step.job_id,
                            ProcessingJobRecord.status == JobStatus.PROCESSING.value,
                        )
                        .values(status=JobStatus.FAILED.value)
                    )
                    step.status = "failed"
                    step.completed_at = datetime.now(UTC)
                    step.error = "worker lease expired; retry limit reached"
                    continue
                result = await session.execute(
                    update(ProcessingJobRecord)
                    .where(
                        ProcessingJobRecord.id == step.job_id,
                        ProcessingJobRecord.status == JobStatus.PROCESSING.value,
                    )
                    .values(status=JobStatus.QUEUED.value)
                )
                if result.rowcount:
                    step.status = "failed"
                    step.completed_at = datetime.now(UTC)
                    step.retry_count += 1
                    step.error = "worker lease expired; job requeued"
                    recovered += 1
            await session.commit()
        return recovered

    async def get_design_spec(self, job_id: UUID) -> DesignSpec:
        async with self._session_factory() as session:
            row = await session.scalar(select(DesignSpecRecord).where(DesignSpecRecord.job_id == str(job_id)))
        return DesignSpec.model_validate(row.document if row else {})

    async def save_design_spec(self, job_id: UUID, spec: DesignSpec) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(DesignSpecRecord).where(DesignSpecRecord.job_id == str(job_id)))
            if row is None:
                session.add(DesignSpecRecord(job_id=str(job_id), schema_version=spec.schema_version, document=spec.model_dump(mode="json")))
            else:
                row.schema_version, row.document = spec.schema_version, spec.model_dump(mode="json")
            await session.commit()

    async def get_processing_settings(self, job_id: UUID) -> ProcessingSettings:
        async with self._session_factory() as session:
            row = await session.scalar(select(ProcessingSettingsRecord).where(ProcessingSettingsRecord.job_id == str(job_id)))
        return ProcessingSettings.model_validate(row.document if row else {})

    async def save_processing_settings(self, job_id: UUID, settings: ProcessingSettings) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(ProcessingSettingsRecord).where(ProcessingSettingsRecord.job_id == str(job_id)))
            if row is None:
                session.add(ProcessingSettingsRecord(job_id=str(job_id), schema_version=settings.schema_version, document=settings.model_dump(mode="json")))
            else:
                row.schema_version, row.document = settings.schema_version, settings.model_dump(mode="json")
            await session.commit()


class JobStepRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def start(self, job_id: UUID, name: str) -> UUID:
        step_id = uuid4()
        async with self._session_factory() as session:
            session.add(JobStepRecord(
                id=str(step_id), job_id=str(job_id), name=name, status="running",
                started_at=datetime.now(UTC), retry_count=0,
            ))
            await session.commit()
        return step_id

    async def complete(self, step_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(JobStepRecord).where(JobStepRecord.id == str(step_id)))
            if row is None:
                raise RuntimeError(f"job step {step_id} not found")
            now = datetime.now(UTC)
            row.status, row.completed_at = "completed", now
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
            await session.commit()

    async def fail(self, step_id: UUID, error: str, retry_count: int = 0) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(JobStepRecord).where(JobStepRecord.id == str(step_id)))
            if row is None:
                raise RuntimeError(f"job step {step_id} not found")
            now = datetime.now(UTC)
            row.status, row.completed_at = "failed", now
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
            row.retry_count, row.error = retry_count, error[-4000:]
            await session.commit()


class ArtifactRepository:
    async def get_expired(self, now: datetime | None = None) -> list[ArtifactRecord]:
        cutoff = now or datetime.now(UTC)
        async with self._session_factory() as session:
            result = await session.scalars(
                select(ArtifactRecord)
                .where(ArtifactRecord.expires_at.is_not(None), ArtifactRecord.expires_at <= cutoff)
                .order_by(ArtifactRecord.expires_at.asc())
            )
            return list(result.all())

    async def delete(self, artifact_id: str) -> None:
        async with self._session_factory() as session:
            row = await session.scalar(select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id))
            if row is not None:
                await session.delete(row)
                await session.commit()

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_for_job(self, job_id: UUID, artifact_type: str | None = None) -> list[ArtifactRecord]:
        async with self._session_factory() as session:
            statement = select(ArtifactRecord).where(ArtifactRecord.job_id == str(job_id))
            if artifact_type is not None:
                statement = statement.where(ArtifactRecord.type == artifact_type)
            statement = statement.order_by(ArtifactRecord.created_at.asc())
            result = await session.scalars(statement)
            return list(result.all())

    async def register(
        self,
        job_id: UUID,
        path: Path,
        artifact_type: str,
        mime_type: str,
        metadata: dict | None = None,
        retention_seconds: int | None = None,
    ) -> ArtifactRecord:
        if not path.is_file():
            raise FileNotFoundError(path)

        detected_mime = guess_type(path.name)[0]
        if detected_mime and detected_mime != mime_type:
            raise ValueError(f"artifact MIME mismatch: expected {mime_type}, detected {detected_mime}")

        digest, size = hashlib.sha256(), 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        sha256 = digest.hexdigest()

        async with self._session_factory() as session:
            existing = await session.scalar(
                select(ArtifactRecord)
                .where(
                    ArtifactRecord.job_id == str(job_id),
                    ArtifactRecord.type == artifact_type,
                    ArtifactRecord.storage_path == str(path),
                )
                .order_by(ArtifactRecord.created_at.desc())
            )
            if existing is not None:
                if existing.sha256 != sha256 or existing.size_bytes != size or existing.mime_type != mime_type:
                    raise ValueError("artifact path already registered with different content")
                return existing

            expires_at = (datetime.now(UTC) + timedelta(seconds=retention_seconds)) if retention_seconds is not None else None
            row = ArtifactRecord(
                artifact_id=str(uuid4()), job_id=str(job_id), type=artifact_type,
                storage_path=str(path), mime_type=mime_type, size_bytes=size,
                sha256=sha256, created_at=datetime.now(UTC), expires_at=expires_at, metadata=metadata or {},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row
