from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ai_gif_studio.application.creative_workflow import CreativeWorkflow
from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission


class Repo:
    def __init__(self, job: ProcessingJob) -> None:
        self.job = job

    async def get(self, _job_id):
        return self.job

    async def set_status(self, _job_id, status, expected_status=None):
        if status == JobStatus.PROCESSING.value:
            return False
        return True

    async def get_design_spec(self, _job_id):
        from ai_gif_studio.domain.specs import DesignSpec
        return DesignSpec()

    async def get_processing_settings(self, _job_id):
        from ai_gif_studio.domain.specs import ProcessingSettings
        return ProcessingSettings()


class Steps:
    async def start(self, *_):
        return uuid4()


class Artifacts:
    async def register(self, *_args, **_kwargs):
        raise AssertionError("rendering must not start after a lost processing claim")


class Engine:
    async def convert(self, *_args, **_kwargs):
        raise AssertionError("rendering must not start after a lost processing claim")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_workflow_fails_closed_when_processing_claim_is_lost(tmp_path: Path) -> None:
    job = ProcessingJob(
        uuid4(),
        JobStatus.QUEUED,
        VideoSubmission("f", "v.mp4", "video/mp4", 10, 7, ProcessingMode.DESIGNED, 1),
        datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="state changed"):
        await CreativeWorkflow(Repo(job), Steps(), Artifacts(), Engine()).run(
            job.id, tmp_path / "source", tmp_path / "out.gif"
        )
