import pytest

from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.database.session import Database
from ai_gif_studio.models import ProcessingMode, VideoSubmission


@pytest.mark.unit
async def test_duplicate_submission_returns_same_job(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'idempotency.db'}")
    await database.create_schema()
    try:
        repository = SqlAlchemyJobRepository(database.session_factory)
        submission = VideoSubmission(
            "telegram-file-1",
            "video.mp4",
            "video/mp4",
            100,
            123,
            ProcessingMode.CROP_ONLY,
            source_message_id=456,
        )

        first = await repository.create(submission)
        second = await repository.create(submission)

        assert second.id == first.id
        assert second.status == first.status
        assert (await repository.count_active()) == 1
    finally:
        await database.dispose()


@pytest.mark.unit
async def test_different_message_ids_create_distinct_jobs(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'idempotency.db'}")
    await database.create_schema()
    try:
        repository = SqlAlchemyJobRepository(database.session_factory)
        first = await repository.create(
            VideoSubmission("file-1", "a.mp4", "video/mp4", 100, 123, source_message_id=1)
        )
        second = await repository.create(
            VideoSubmission("file-2", "b.mp4", "video/mp4", 100, 123, source_message_id=2)
        )

        assert second.id != first.id
        assert (await repository.count_active()) == 2
    finally:
        await database.dispose()
