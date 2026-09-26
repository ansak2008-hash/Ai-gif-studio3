from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from ai_gif_studio.database.repositories import ArtifactRepository, JobStepRepository
from ai_gif_studio.engines.design_production2 import ProductionDesignGifEngine
from ai_gif_studio.models import JobStatus


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    job_id: UUID
    artifact_path: Path
    size_bytes: int


class CreativeWorkflow:
    """Orchestrates one durable video-to-GIF job; transport adapters stay outside it."""

    def __init__(self, repository, steps: JobStepRepository, artifacts: ArtifactRepository, engine: ProductionDesignGifEngine):
        self.repository = repository
        self.steps = steps
        self.artifacts = artifacts
        self.engine = engine

    async def run(self, job_id: UUID, source: Path, target: Path) -> WorkflowResult:
        job = await self.repository.get(job_id)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        if job.status not in {JobStatus.QUEUED, JobStatus.PROCESSING}:
            raise ValueError(f"job is not processable from state: {job.status.value}")
        if job.status is JobStatus.QUEUED:
            await self.repository.set_status(job_id, JobStatus.PROCESSING.value, expected_status=JobStatus.QUEUED.value)
        design = await self.repository.get_design_spec(job_id)
        settings = await self.repository.get_processing_settings(job_id)
        step_id = await self.steps.start(job_id, "render")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            await self.engine.convert(source, target, design, settings)
            artifact = await self.artifacts.register(job_id, target, "gif", "image/gif", metadata={"workflow": "creative"})
            await self.steps.complete(step_id)
            await self.repository.set_status(job_id, JobStatus.COMPLETED.value, expected_status=JobStatus.PROCESSING.value)
            return WorkflowResult(job_id, Path(artifact.storage_path), artifact.size_bytes)
        except Exception as exc:
            await self.steps.fail(step_id, str(exc))
            await self.repository.set_status(job_id, JobStatus.FAILED.value, expected_status=JobStatus.PROCESSING.value)
            raise
