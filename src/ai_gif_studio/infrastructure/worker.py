from __future__ import annotations
import asyncio
from pathlib import Path
from arq.connections import RedisSettings
from arq import Worker
from aiogram import Bot
from ai_gif_studio.configuration import AppSettings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.infrastructure.storage import ArtifactStorage
from ai_gif_studio.domain.specs import ProcessingSettings
async def process_job(ctx,job_id:str,**_):
    s=ctx["settings"]; db=Database(s.database_url); repo=SqlAlchemyJobRepository(db.session_factory); job=await repo.get(__import__("uuid").UUID(job_id))
    if job is None: await db.dispose(); raise RuntimeError("job not found")
    bot=Bot(s.telegram_bot_token); storage=ArtifactStorage(str(s.storage_directory)); work=storage.job_dir(job.id)
    source=work/"input.bin"; output=work/"output.gif"
    try:
        await repo.set_status(job.id,"processing")
        await bot.download(job.submission.telegram_file_id,destination=source)
        engine=CropOnlyEngine(FFmpegService(s.ffmpeg_binary,s.ffprobe_binary,s.worker_timeout_seconds))
        await engine.convert(source,output,ProcessingSettings(max_duration_seconds=min(6,s.max_duration_seconds)))
        await repo.set_status(job.id,"completed")
        await bot.send_document(job.submission.submitted_by,output)
    except Exception as exc:
        await repo.set_status(job.id,"failed")
        raise
    finally:
        await bot.session.close(); await db.dispose()
class WorkerSettings:
    functions=[process_job]
    max_jobs=2
    job_timeout=180
    @staticmethod
    def redis_settings():
        return RedisSettings.from_dsn(AppSettings().redis_url)
