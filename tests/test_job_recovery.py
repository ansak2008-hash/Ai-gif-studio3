from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from ai_gif_studio.database.repositories import JobStepRepository, SqlAlchemyJobRepository
from ai_gif_studio.database.session import Database
from ai_gif_studio.database.tables import JobStepRecord
from ai_gif_studio.models import JobStatus, ProcessingMode, VideoSubmission


@pytest.mark.unit
async def test_stale_processing_job_is_requeued_and_step_is_failed(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'recovery.db'}")
    await database.create_schema()
    try:
        repository = SqlAlchemyJobRepository(database.session_factory)
        job = await repository.create(
            VideoSubmission("file", "video.mp4", "video/mp4", 10, 7, ProcessingMode.CROP_ONLY, 9)
        )
        await repository.set_status(job.id, "queued", expected_status="created")
        await repository.set_status(job.id, "processing", expected_status="queued")

        steps = JobStepRepository(database.session_factory)
        step_id = await steps.start(job.id, "render")
        stale = datetime.now(UTC) - timedelta(minutes=10)
        async with database.session_factory() as session:
            await session.execute(
                update(JobStepRecord)
                .where(JobStepRecord.id == str(step_id))
                .values(started_at=stale)
            )
            await session.commit()

        recovered = await repository.recover_stale_processing(
            datetime.now(UTC) - timedelta(minutes=5), max_retries=2
        )

        assert recovered == 1
        assert (await repository.get(job.id)).status == JobStatus.QUEUED
        async with database.session_factory() as session:
            step = await session.scalar(
                select(JobStepRecord).where(JobStepRecord.id == str(step_id))
            )
            assert step.status == "failed"
            assert step.retry_count == 1
    finally:
        await database.dispose()


@pytest.mark.unit
async def test_stale_job_reaches_failed_after_retry_limit(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'recovery.db'}")
    await database.create_schema()
    try:
        repository = SqlAlchemyJobRepository(database.session_factory)
        job = await repository.create(
            VideoSubmission("file", "video.mp4", "video/mp4", 10, 7, ProcessingMode.CROP_ONLY, 10)
        )
        await repository.set_status(job.id, "queued", expected_status="created")
        await repository.set_status(job.id, "processing", expected_status="queued")
        steps = JobStepRepository(database.session_factory)
        step_id = await steps.start(job.id, "render")
        stale = datetime.now(UTC) - timedelta(minutes=10)
        async with database.session_factory() as session:
            await session.execute(
                update(JobStepRecord)
                .where(JobStepRecord.id == str(step_id))
                .values(started_at=stale, retry_count=2)
            )
            await session.commit()

        assert await repository.recover_stale_processing(
            datetime.now(UTC) - timedelta(minutes=5), max_retries=2
        ) == 0
        assert (await repository.get(job.id)).status == JobStatus.FAILED
    finally:
        await database.dispose()
