import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from ai_gif_studio.database.repositories import ArtifactRepository
from ai_gif_studio.database.session import Database
from ai_gif_studio.domain.artifact import make_artifact_id

pytestmark = pytest.mark.unit
async def test_artifact_registration_is_retry_safe(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'artifacts.db'}")
    await database.create_schema()
    try:
        job_id = uuid4()
        output = tmp_path / "output.gif"
        output.write_bytes(b"GIF89a-test-artifact")
        repository = ArtifactRepository(database.session_factory)
        first = await repository.register(job_id, output, "output_gif", "image/gif", metadata={"fps": 12})
        second = await repository.register(job_id, output, "output_gif", "image/gif", metadata={"fps": 12})
        assert first.artifact_id == second.artifact_id
        assert second.sha256 == first.sha256
        assert second.size_bytes == len(b"GIF89a-test-artifact")
        artifacts = await repository.get_for_job(job_id, "output_gif")
        assert len(artifacts) == 1
    finally:
        await database.dispose()

async def test_concurrent_artifact_registration_is_single_record(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'concurrent-artifacts.db'}")
    await database.create_schema()
    try:
        job_id = uuid4()
        output = tmp_path / "output.gif"
        output.write_bytes(b"GIF89a-concurrent-artifact")
        repository = ArtifactRepository(database.session_factory)
        results = await asyncio.gather(
            *(repository.register(job_id, output, "output_gif", "image/gif") for _ in range(32))
        )
        assert len({result.artifact_id for result in results}) == 1
        expected_id = make_artifact_id(job_id, "output_gif", str(output))
        assert results[0].artifact_id == str(expected_id)
        artifacts = await repository.get_for_job(job_id, "output_gif")
        assert len(artifacts) == 1
    finally:
        await database.dispose()

async def test_artifact_registration_rejects_changed_content_at_same_path(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'artifacts.db'}")
    await database.create_schema()
    try:
        job_id = uuid4()
        output = tmp_path / "output.gif"
        output.write_bytes(b"GIF89a-first")
        repository = ArtifactRepository(database.session_factory)
        await repository.register(job_id, output, "output_gif", "image/gif")
        output.write_bytes(b"GIF89a-second")
        with pytest.raises(ValueError, match="different content"):
            await repository.register(job_id, output, "output_gif", "image/gif")
    finally:
        await database.dispose()
