from dataclasses import dataclass

import pytest

from ai_gif_studio.models import ProcessingJob, VideoSubmission
from ai_gif_studio.services import IntakeError, IntakeService


@dataclass
class FakeRepository:
    job: ProcessingJob | None = None

    async def create(self, submission: VideoSubmission) -> ProcessingJob:
        assert self.job is not None
        return self.job

    async def count_active(self) -> int:
        return 0


@pytest.mark.asyncio
async def test_intake_rejects_video_larger_than_limit() -> None:
    service = IntakeService(FakeRepository(), max_upload_bytes=10, allowed_user_ids=())
    with pytest.raises(IntakeError, match="exceeds"):
        await service.receive_video(VideoSubmission("id", None, None, 11, 1))
