from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from ai_gif_studio.database.repositories import ArtifactRepository
from ai_gif_studio.database.session import Database
from ai_gif_studio.services.artifact_retention import ArtifactRetentionService


@pytest.mark.unit
async def test_artifact_retention_sets_expiry_and_cleanup_removes_file(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'artifacts.db'}")
    await database.create_schema()
    try:
        output = tmp_path / "output.gif"
        output.write_bytes(b"GIF89a-retained")
        repository = ArtifactRepository(database.session_factory)
        artifact = await repository.register(
            uuid4(), output, "output_gif", "image/gif", retention_seconds=60
        )
        assert artifact.expires_at is not None
        assert artifact.expires_at is not None

        service = ArtifactRetentionService(repository)
        removed = await service.cleanup_expired(artifact.expires_at + timedelta(seconds=1))

        assert removed == 1
        assert not output.exists()
        assert await repository.get_expired(artifact.expires_at + timedelta(seconds=1)) == []
    finally:
        await database.dispose()


@pytest.mark.unit
async def test_retention_does_not_delete_unexpired_artifact(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'artifacts.db'}")
    await database.create_schema()
    try:
        output = tmp_path / "output.gif"
        output.write_bytes(b"GIF89a-retained")
        repository = ArtifactRepository(database.session_factory)
        artifact = await repository.register(
            uuid4(), output, "output_gif", "image/gif", retention_seconds=3600
        )
        service = ArtifactRetentionService(repository)
        assert await service.cleanup_expired(datetime.now(UTC)) == 0
        assert output.exists()
        assert await repository.get_expired(datetime.now(UTC)) == []
        assert artifact.artifact_id
    finally:
        await database.dispose()
