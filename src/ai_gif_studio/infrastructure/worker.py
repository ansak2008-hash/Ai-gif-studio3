from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from aiogram.types import FSInputFile
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
    source = work / "input.bin"
    output = work / "output.gif"
    steps = (
        "download",
        "probe",
        "crop_encode",
        "artifact_register",
        "delivery",
    )
    active_step = None
    try:
        if not await repo.set_status(job.id, "processing", expected_status="queued"):
            raise RuntimeError(f"job {job.id} is not in queued state")

        active_step = await step_repo.start(job.id, steps[0])
        await bot.download(job.submission.telegram_file_id, destination=source)
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[1])
        ff = FFmpegService(
            settings.ffmpeg_binary, settings.ffprobe_binary, settings.worker_timeout_seconds
        )
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

        active_step = await step_repo.start(job.id, steps[2])
        engine = CropOnlyEngine(ff)
        await engine.convert(
            source,
            output,
            ProcessingSettings(max_duration_seconds=min(6, duration or 6)),
        )
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[3])
        await ArtifactRepository(db.session_factory).register(
            job.id, output, "output_gif", "image/gif"
        )
        await step_repo.complete(active_step)

        active_step = await step_repo.start(job.id, steps[4])
        await bot.send_document(job.submission.submitted_by, FSInputFile(output))
        await step_repo.complete(active_step)

        await repo.set_status(job.id, "completed", expected_status="processing")
    except Exception as error:
        if active_step is not None:
            retry_count = int(ctx.get("job_try", 1)) - 1
            await step_repo.fail(active_step, str(error), retry_count)
        is_last_try = int(ctx.get("job_try", 1)) >= int(ctx.get("max_tries", 1))
        await repo.set_status(
            job.id,
            "failed" if is_last_try else "queued",
            expected_status="processing",
        )
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
