from pathlib import Path
from uuid import uuid4

import pytest

from ai_gif_studio.application.creative_workflow import CreativeWorkflow
from ai_gif_studio.models import JobStatus, ProcessingJob, ProcessingMode, VideoSubmission


class Repo:
    def __init__(self, job): self.job = job; self.statuses = []
    async def get(self, _): return self.job
    async def set_status(self, _, status, expected_status=None):
        self.statuses.append((status, expected_status)); self.job = ProcessingJob(self.job.id, JobStatus(status), self.job.submission, self.job.created_at); return True
    async def get_design_spec(self, _):
        from ai_gif_studio.domain.specs import DesignSpec
        return DesignSpec()
    async def get_processing_settings(self, _):
        from ai_gif_studio.domain.specs import ProcessingSettings
        return ProcessingSettings()

class Steps:
    async def start(self, *_): return uuid4()
    async def complete(self, *_): pass
    async def fail(self, *_): pass

class Artifacts:
    async def register(self, job_id, path, *_args, **_kwargs):
        return type("A", (), {"storage_path": str(path), "size_bytes": 123})()

class Engine:
    async def convert(self, source, target, *_): target.write_bytes(b"GIF89a")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_workflow_transitions_and_registers_artifact(tmp_path: Path):
    job = ProcessingJob(uuid4(), JobStatus.QUEUED, VideoSubmission("f", "v.mp4", "video/mp4", 10, 7, ProcessingMode.DESIGNED, 1), __import__("datetime").datetime.now(__import__("datetime").UTC))
    repo = Repo(job)
    result = await CreativeWorkflow(repo, Steps(), Artifacts(), Engine()).run(job.id, tmp_path / "source", tmp_path / "out.gif")
    assert result.artifact_path.name == "out.gif"
    assert repo.statuses == [("processing", "queued"), ("completed", "processing")]
