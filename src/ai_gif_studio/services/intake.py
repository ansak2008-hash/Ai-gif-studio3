from __future__ import annotations

from ai_gif_studio.database.repositories import JobRepository
from ai_gif_studio.models import ProcessingJob, VideoSubmission


class IntakeError(ValueError):
    pass


class IntakeService:
    """Validates and durably registers input; it never misrepresents processing state."""

    def __init__(
        self, repository: JobRepository, max_upload_bytes: int, allowed_user_ids: tuple[int, ...]
    ) -> None:
        self._repository = repository
        self._max_upload_bytes = max_upload_bytes
        self._allowed_user_ids = allowed_user_ids

    async def receive_video(self, submission: VideoSubmission) -> ProcessingJob:
        if self._allowed_user_ids and submission.submitted_by not in self._allowed_user_ids:
            raise IntakeError("This user is not authorized to use this bot.")
        if submission.file_size_bytes > self._max_upload_bytes:
            raise IntakeError("This video exceeds the configured upload limit.")
        return await self._repository.create(submission)

    async def mark_queued(self, job: ProcessingJob) -> None:
        setter = getattr(self._repository, "set_status", None)
        if setter is not None:
            await setter(job.id, "queued")
