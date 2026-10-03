from __future__ import annotations

import logging
import os
import socket
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
from ai_gif_studio.domain.delivery_contract import DeliveryConfig, DeliveryState, SendDecision, decide_send
from ai_gif_studio.domain.job_queue import AtomicJobQueue
from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.engines.design import DesignGifEngine
from ai_gif_studio.engines.validator import OutputValidator
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.infrastructure.recovery import cron_settings
from ai_gif_studio.infrastructure.storage import ArtifactStorage

logger = logging.getLogger(__name__)


async def process_job(ctx, job_id: str, **_):
    settings = ctx["settings"]
    db = Database(settings.database_url)
    repo = SqlAlchemyJobRepository(db.session_factory)
    queue = AtomicJobQueue(repo)
    step_repo = JobStepRepository(db.session_factory)
    job = await repo.get(UUID(job_id))
    if job is None:
        await db.dispose()
        raise RuntimeError("job not found")

    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    claimed = await queue.claim_for_processing(job.id, worker_id)
    if claimed is None:
        await db.dispose()
        return
    job = claimed.job

    bot = Bot(settings.telegram_bot_token)
    storage = ArtifactStorage(str(settings.storage_directory))
    work = storage.job_dir(job.id)
    source, output = work / "input.bin", work / "output.gif"
    steps = ("download", "probe", "render", "quality", "artifact_register", "delivery")
    active_step = None
    failure_reason = "internal_error"
    failure_stage = "job"
    try:
        failure_stage = "download"
        active_step = await step_repo.start(job.id, steps[0])
        await bot.download(job.submission.telegram_file_id, destination=source)
        await step_repo.complete(active_step)

        failure_stage = "probe"
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

        failure_stage = "render"
        active_step = await step_repo.start(job.id, steps[2])
        if job.submission.mode.value == "designed":
            await DesignGifEngine(ff).convert(source, output, design, processing)
        else:
            await CropOnlyEngine(ff).convert(source, output, processing)
        await step_repo.complete(active_step)

        failure_stage = "quality_inspect"
        active_step = await step_repo.start(job.id, steps[3])
        from ai_gif_studio.quality_engine import QualityEngine
        report = await QualityEngine().inspect(output, ff, processing.max_bytes, selected_fps=processing.fps)
        if not report.valid:
            failure_reason = "invalid_media"
            raise ValueError(f"quality gate failed: {report.as_dict()}")
        await step_repo.complete(active_step)

        failure_stage = "artifact_register"
        active_step = await step_repo.start(job.id, steps[4])
        if not await OutputValidator(ff).validate_gif(output, max_bytes=processing.max_bytes, ffmpeg=ff):
            raise ValueError("rendered GIF failed output validation")
        artifact = await ArtifactRepository(db.session_factory).register(
            job.id,
            output,
            "output_gif",
            "image/gif",
            metadata={
                "design_spec_version": design.schema_version,
                "processing_settings_version": processing.schema_version,
                "quality": report.as_dict(),
            },
        )
        await step_repo.complete(active_step)

        failure_stage = "delivery"
        active_step = await step_repo.start(job.id, steps[5])
        from ai_gif_studio.database.repositories import SqlAlchemyDeliveryLog
        from ai_gif_studio.domain.delivery_contract import DeliveryIdentity

        delivery_log = SqlAlchemyDeliveryLog(db.session_factory)
        delivery_config = DeliveryConfig(max_attempts=3)
        identity = DeliveryIdentity(job.id, UUID(artifact.artifact_id), "telegram")
        record = await delivery_log.begin_delivery(identity)
        decision = decide_send(record, delivery_config)
        if decision is SendDecision.RETRY:
            record = await delivery_log.begin_retry(identity, delivery_config.max_attempts)
            if record is None:
                raise RuntimeError("delivery retry lost its durable state")
            decision = SendDecision.SEND
        if decision is SendDecision.SKIP_SENT:
            pass
        elif decision is SendDecision.SEND:
            try:
                message = await bot.send_document(
                    job.submission.submitted_by,
                    FSInputFile(output),
                )
            except Exception as error:
                await delivery_log.mark_failed(identity, str(error))
                raise
            await delivery_log.mark_sent(identity, str(message.message_id))
        elif decision is SendDecision.HOLD_UNKNOWN:
            await delivery_log.mark_unknown(identity)
            raise RuntimeError("delivery outcome is unknown; manual resolution required")
        else:
            if record.state is DeliveryState.FAILED:
                await delivery_log.mark_terminal(identity, "delivery retry budget exhausted")
            raise RuntimeError("delivery retries exhausted; manual resolution required")
        await step_repo.complete(active_step)
        await queue.complete(job.id, worker_id, claimed.version)
    # Intentional job-boundary containment: classify and persist every terminal job failure.
    except Exception as error:
        failure = f"{failure_reason}: {error}"
        if failure_reason == "internal_error":
            logger.error(
                "INTERNAL_ERROR job=%s stage=%s",
                job_id,
                failure_stage,
                exc_info=True,
            )
        if active_step is not None:
            await step_repo.fail(active_step, failure, max(0, int(ctx.get("job_try", 1)) - 1))
        job_try = int(ctx.get("job_try", 1))
        if job_try < 2:
            if not await queue.retry(job.id, worker_id, claimed.version, failure):
                raise RuntimeError("job claim was lost before retry") from error
            raise Retry(defer=job_try * 5) from error
        await queue.fail(job.id, worker_id, claimed.version, failure)
        raise
    finally:
        await bot.session.close()
        await db.dispose()


class WorkerSettings:
    functions = [process_job]
    cron_jobs = [cron_settings()]
    max_jobs = 2
    max_tries = 2
    job_timeout = 180
    redis_settings = RedisSettings.from_dsn(AppSettings().redis_url)
