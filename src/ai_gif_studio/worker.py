from __future__ import annotations

import logging
import os
import socket
import sys
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
from ai_gif_studio.domain.job_queue import AtomicJobQueue
from ai_gif_studio.engines.design_production2 import ProductionDesignGifEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.observability import stage

logger = logging.getLogger(__name__)


async def _cleanup_resources(
    *,
    source: Path | None,
    bot: Bot | None,
    db: Database,
) -> list[BaseException]:
    errors: list[BaseException] = []

    if source is not None:
        try:
            source.unlink(missing_ok=True)
        except BaseException as exc:
            errors.append(exc)

    if bot is not None:
        try:
            await bot.session.close()
        except BaseException as exc:
            errors.append(exc)

    try:
        await db.dispose()
    except BaseException as exc:
        errors.append(exc)

    return errors


def _log_cleanup_errors(errors: list[BaseException], job_id: str | None) -> None:
    for error in errors:
        logger.error(
            "resource_cleanup_failed job_id=%s error=%s",
            job_id,
            type(error).__name__,
        )


async def process_job(ctx, job_id: str):
    settings = get_settings()
    db = Database(settings.database_url)
    if not settings.telegram_bot_token:
        await db.dispose()
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be configured for Telegram delivery")

    bot: Bot | None = None
    source: Path | None = None
    try:
        bot = Bot(settings.telegram_bot_token)
        repo = SqlAlchemyJobRepository(db.session_factory)
        queue = AtomicJobQueue(repo)
        job = await repo.get(UUID(job_id))
        if job is None:
            logger.warning("job_missing job_id=%s", job_id)
            return {"status": "missing", "job_id": job_id}

        worker_id = f"{socket.gethostname()}:{os.getpid()}"
        claimed = await queue.claim_for_processing(job.id, worker_id)
        if claimed is None:
            logger.info("worker_claim_lost job_id=%s worker_id=%s", job_id, worker_id)
            return {"status": "claim_lost", "job_id": job_id}

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
                )
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
        primary_error = sys.exc_info()[1]
        errors = await _cleanup_resources(source=source, bot=bot, db=db)
        if errors:
            _log_cleanup_errors(errors, job_id)
            if primary_error is None:
                raise errors[0]


class WorkerSettings:
    functions = [process_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = get_settings().worker_timeout_seconds + 30
