from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from aiogram import Bot
from aiogram.types import FSInputFile
from arq.connections import RedisSettings

from ai_gif_studio.application import CreativeWorkflow
from ai_gif_studio.configuration import get_settings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import (
    ArtifactRepository,
    JobStepRepository,
    SqlAlchemyJobRepository,
)
from ai_gif_studio.engines.design_production2 import ProductionDesignGifEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.observability import stage

logger = logging.getLogger(__name__)


async def process_job(ctx, job_id: str):
    settings = get_settings()
    db = Database(settings.database_url)
    if not settings.telegram_bot_token:
        await db.dispose()
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be configured for Telegram delivery")
    bot = Bot(settings.telegram_bot_token)
    source: Path | None = None
    try:
        repo = SqlAlchemyJobRepository(db.session_factory)
        job = await repo.get(UUID(job_id))
        if job is None:
            logger.warning("job_missing job_id=%s", job_id)
            return {"status": "missing", "job_id": job_id}
        source = settings.temp_directory / f"{job.id}.source"
        target = settings.storage_directory / f"{job.id}.gif"
        source.parent.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with stage(job.id, "download"):
            tg_file = await bot.get_file(job.submission.telegram_file_id)
            await bot.download(tg_file, destination=source)
        workflow = CreativeWorkflow(
            repo,
            JobStepRepository(db.session_factory),
            ArtifactRepository(db.session_factory),
            ProductionDesignGifEngine(
                FFmpegService(
                    settings.ffmpeg_binary,
                    settings.ffprobe_binary,
                    settings.worker_timeout_seconds,
                ),
                max_input_bytes=settings.max_upload_bytes,
                max_input_width=settings.max_width,
                max_input_height=settings.max_height,
                max_input_duration_seconds=settings.max_duration_seconds,
            ),
        )
        async with stage(job.id, "render"):
            result = await workflow.run(UUID(job_id), source, target)
        async with stage(job.id, "delivery"):
            await bot.send_document(
                job.submission.submitted_by,
                FSInputFile(result.artifact_path),
            )
        return {"status": "completed", "job_id": job_id, "size_bytes": result.size_bytes}
    finally:
        if source is not None:
            source.unlink(missing_ok=True)
        await bot.session.close()
        await db.dispose()


class WorkerSettings:
    functions = [process_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = get_settings().worker_timeout_seconds + 30
