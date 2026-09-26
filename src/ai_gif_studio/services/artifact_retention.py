from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_gif_studio.database.repositories import ArtifactRepository


class ArtifactRetentionService:
    """Delete expired artifact files and their registry records."""

    def __init__(self, repository: ArtifactRepository) -> None:
        self._repository = repository

    async def cleanup_expired(self, now: datetime | None = None) -> int:
        removed = 0
        for artifact in await self._repository.get_expired(now or datetime.now(UTC)):
            path = Path(artifact.storage_path)
            try:
                path.unlink(missing_ok=True)
                await self._repository.delete(artifact.artifact_id)
                removed += 1
            except OSError:
                continue
        return removed
