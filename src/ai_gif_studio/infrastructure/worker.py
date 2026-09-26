from __future__ import annotations
from arq.connections import RedisSettings
from arq import Worker
from aiogram import Bot
from aiogram.types import FSInputFile
from ai_gif_studio.configuration import AppSettings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository,ArtifactRepository
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.infrastructure.storage import ArtifactStorage
from ai_gif_studio.domain.specs import ProcessingSettings
async def process_job(ctx,job_id:str,**_):
    s=ctx["settings"]; db=Database(s.database_url); repo=SqlAlchemyJobRepository(db.session_factory); job=await repo.get(__import__("uuid").UUID(job_id))
    if job is None: await db.dispose(); raise RuntimeError("job not found")
    bot=Bot(s.telegram_bot_token); storage=ArtifactStorage(str(s.storage_directory)); work=storage.job_dir(job.id); source=work/"input.bin"; output=work/"output.gif"
    try:
        await repo.set_status(job.id,"processing")
        await bot.download(job.submission.telegram_file_id,destination=source)
        ff=FFmpegService(s.ffmpeg_binary,s.ffprobe_binary,s.worker_timeout_seconds); probe=await ff.probe(source)
        video=next((x for x in probe.get("streams",[]) if x.get("codec_type")=="video"),None)
        if not video: raise ValueError("input has no video stream")
        if int(video.get("width",0))>s.max_width or int(video.get("height",0))>s.max_height: raise ValueError("input resolution exceeds configured limit")
        duration=float(probe.get("format",{}).get("duration") or 0)
        if duration>s.max_duration_seconds: raise ValueError("input duration exceeds configured limit")
        engine=CropOnlyEngine(ff); await engine.convert(source,output,ProcessingSettings(max_duration_seconds=min(6,duration or 6)))
        await ArtifactRepository(db.session_factory).register(job.id,output,"output_gif","image/gif")
        await repo.set_status(job.id,"completed"); await bot.send_document(job.submission.submitted_by,FSInputFile(output))
    except Exception:
        await repo.set_status(job.id,"failed"); raise
    finally:
        await bot.session.close(); await db.dispose()
class WorkerSettings:
    functions=[process_job]; max_jobs=2; job_timeout=180; redis_settings=RedisSettings.from_dsn(AppSettings().redis_url)
