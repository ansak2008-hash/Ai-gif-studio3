import pytest

from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.database.session import Database
from ai_gif_studio.models import JobStatus, ProcessingMode, VideoSubmission, can_transition


@pytest.mark.unit
def test_job_transition_matrix_is_explicit() -> None:
    assert can_transition(JobStatus.CREATED, JobStatus.QUEUED)
    assert can_transition(JobStatus.QUEUED, JobStatus.PROCESSING)
    assert can_transition(JobStatus.PROCESSING, JobStatus.COMPLETED)
    assert can_transition(JobStatus.PROCESSING, JobStatus.FAILED)
    assert can_transition(JobStatus.PROCESSING, JobStatus.QUEUED)
    assert not can_transition(JobStatus.COMPLETED, JobStatus.PROCESSING)
    assert not can_transition(JobStatus.FAILED, JobStatus.QUEUED)


@pytest.mark.unit
async def test_repository_rejects_invalid_job_transition(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")
    await database.create_schema()
    try:
        repository = SqlAlchemyJobRepository(database.session_factory)
        job = await repository.create(
            VideoSubmission("file", "video.mp4", "video/mp4", 1, 123, ProcessingMode.CROP_ONLY)
        )
        assert await repository.set_status(job.id, "queued", expected_status="created")
        assert await repository.set_status(job.id, "processing", expected_status="queued")
        with pytest.raises(ValueError, match="invalid job transition"):
            await repository.set_status(job.id, "created")
        assert (await repository.get(job.id)).status == JobStatus.PROCESSING
    finally:
        await database.dispose()
