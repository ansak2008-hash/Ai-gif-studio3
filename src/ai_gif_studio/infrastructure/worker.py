from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from aiogram.types import FSInputFile
from arq import Retry
from arq.connections import RedisSettings

from ai_gif_studio.configuration import AppSettings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import (
    ArtifactRepository,
    JobStepRepository,
    SqlAlchemyJobRepository,
)
from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.engines.design import DesignGifEngine
from ai_gif_studio.engines.validator import OutputValidator
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.infrastructure.storage import ArtifactStorage


async def process_job(ctx, job_id: str, **_):
    settings = ctx["settings"]
    db = Database(settings.database_url)
    repo = SqlAlchemyJobRepository(db.session_factory)
    step_repo = JobStepRepository(db.session_factory)
    job = await repo.get(UUID(job_id))
    if job is None:
        await db.dispose()
        raise RuntimeError("job not found")

    bot = Bot(settings.telegram_bot_token)
    storage = ArtifactStorage(str(settings.storage_directory))
    work = storage.job_dir(job.id)
    source, output = work / "input.bin", work / "output.gif"
    steps = ("download", "probe", "render", "quality", "artifact_register", "delivery")
    active_step = None
    try:
        if not await repo.set_status(job.id, "processing", expected_status="queued"):
            raise RuntimeError(f"job {job.id} is not in queued state")

        active_step = await step_repo.start(job.id, steps[0])
        await bot.download(job.submission.telegram_file_id, destination=source)
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[1])
        ff = FFmpegService(settings.ffmpeg_binary, settings.ffprobe_binary, settings.worker_timeout_seconds)
        probe = await ff.probe(source)
        video = next((x for x in probe.get("streams", []) if x.get("codec_type") == "video"), None)
        if not video:
            raise ValueError("input has no video stream")
        if int(video.get("width", 0)) > settings.max_width or int(video.get("height", 0)) > settings.max_height:
            raise ValueError("input resolution exceeds configured limit")
        duration = float(probe.get("format", {}).get("duration") or 0)
        if duration > settings.max_duration_seconds:
            raise ValueError("input duration exceeds configured limit")
        await step_repo.complete(active_step)

        processing = await repo.get_processing_settings(job.id)
        processing = ProcessingSettings(**{**processing.model_dump(), "max_duration_seconds": min(6.0, duration or 6.0)})
        await repo.save_processing_settings(job.id, processing)
        design = await repo.get_design_spec(job.id)

        active_step = await step_repo.start(job.id, steps[2])
        if job.submission.mode.value == "designed":
            await DesignGifEngine(
                ff,
                max_input_bytes=settings.max_upload_bytes,
                max_input_width=settings.max_width,
                max_input_height=settings.max_height,
                max_input_duration_seconds=settings.max_duration_seconds,
            ).convert(source, output, design, processing)
        else:
            await CropOnlyEngine(ff).convert(source, output, processing)
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[3])
        from ai_gif_studio.quality_engine import QualityEngine
        report = await QualityEngine().inspect(output, ff, processing.max_bytes, selected_fps=processing.fps)
        if not report.valid:
            raise ValueError(f"quality gate failed: {report.as_dict()}")
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[4])
        if not await OutputValidator(ff).validate_gif(output, max_bytes=processing.max_bytes, ffmpeg=ff):
            raise ValueError("rendered GIF failed output validation")
        await ArtifactRepository(db.session_factory).register(
            job.id, output, "output_gif", "image/gif",
            metadata={"design_spec_version": design.schema_version, "processing_settings_version": processing.schema_version, "quality": report.as_dict()},
        )
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[5])
        await bot.send_document(job.submission.submitted_by, FSInputFile(output))
        await step_repo.complete(active_step)
        if not await repo.set_status(job.id, "completed", expected_status="processing"):
            raise RuntimeError("job completion state transition failed")
    except Exception as error:
        if active_step is not None:
            await step_repo.fail(active_step, str(error), max(0, int(ctx.get("job_try", 1)) - 1))
        job_try = int(ctx.get("job_try", 1))
        if job_try < 2:
            await repo.set_status(job.id, "queued", expected_status="processing")
            raise Retry(defer=job_try * 5) from error
        await repo.set_status(job.id, "failed", expected_status="processing")
        raise
    finally:
        await bot.session.close()
        await db.dispose()


class WorkerSettings:
    functions = [process_job]
    max_jobs = 2
    max_tries = 2
    job_timeout = 180
    redis_settings = RedisSettings.from_dsn(AppSettings().redis_url)
