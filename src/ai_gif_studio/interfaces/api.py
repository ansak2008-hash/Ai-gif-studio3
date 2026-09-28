from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai_gif_studio.application.capabilities import CAPABILITIES
from ai_gif_studio.configuration import AppSettings, get_settings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings

READINESS_TIMEOUT_SECONDS = 2.0


async def _check_database(database_url: str) -> bool:
    engine = create_async_engine(database_url)
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


async def _check_redis(redis_url: str) -> bool:
    redis = None
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            redis = await create_pool(RedisSettings.from_dsn(redis_url))
            await redis.ping()
        return True
    except Exception:
        return False
    finally:
        if redis is not None:
            await redis.close()


async def _check_ffmpeg(binary: str) -> bool:
    process = None
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            process = await asyncio.create_subprocess_exec(
                binary,
                "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return await process.wait() == 0
    except Exception:
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
        return False


async def _readiness_checks(settings: AppSettings) -> dict[str, bool]:
    database, redis, ffmpeg = await asyncio.gather(
        _check_database(settings.database_url),
        _check_redis(settings.redis_url),
        _check_ffmpeg(settings.ffmpeg_binary),
    )
    return {"database": database, "redis": redis, "ffmpeg": ffmpeg}


def create_api(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AI Creative GIF Studio", version="0.3.0")

    async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if not settings.api_key:
            if settings.environment == "production":
                raise HTTPException(status_code=503, detail="API authentication is not configured")
            return
        if x_api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid API key",
            )

    @app.middleware("http")
    async def security_context(request: Request, call_next):
        declared_length = request.headers.get("content-length")
        if declared_length is not None:
            try:
                if int(declared_length) > settings.max_request_bytes:
                    return Response(status_code=413, content="request body too large")
            except ValueError:
                return Response(status_code=400, content="invalid content-length")
        request_id = request.headers.get("x-request-id", "")
        if not request_id or len(request_id) > 128 or any(
            ord(c) < 32 or ord(c) == 127 for c in request_id
        ):
            request_id = uuid4().hex
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["cache-control"] = "no-store"
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        checks = await _readiness_checks(settings)
        if not all(checks.values()):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "checks": checks},
            )
        return {"status": "ready", "checks": checks}

    @app.get("/v1/capabilities", dependencies=[Depends(require_api_key)])
    async def capabilities():
        return {
            key: {"state": value.state, "requirements": value.requirements}
            for key, value in CAPABILITIES.items()
        }

    @app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_api_key)])
    async def get_job(job_id: UUID):
        db = Database(settings.database_url)
        try:
            repo = SqlAlchemyJobRepository(db.session_factory)
            job = await repo.get(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="job not found")
            return {
                "id": str(job.id),
                "status": job.status.value,
                "mode": job.submission.mode.value,
                "design_spec": (await repo.get_design_spec(job.id)).model_dump(mode="json"),
                "processing_settings": (
                    await repo.get_processing_settings(job.id)
                ).model_dump(mode="json"),
            }
        finally:
            await db.dispose()

    @app.put("/v1/jobs/{job_id}/design", dependencies=[Depends(require_api_key)])
    async def set_design(job_id: UUID, spec: DesignSpec):
        db = Database(settings.database_url)
        try:
            repo = SqlAlchemyJobRepository(db.session_factory)
            if await repo.get(job_id) is None:
                raise HTTPException(status_code=404, detail="job not found")
            await repo.save_design_spec(job_id, spec)
            return {"job_id": str(job_id), "design_spec": spec.model_dump(mode="json")}
        finally:
            await db.dispose()

    @app.put("/v1/jobs/{job_id}/processing", dependencies=[Depends(require_api_key)])
    async def set_processing(job_id: UUID, payload: ProcessingSettings):
        db = Database(settings.database_url)
        try:
            repo = SqlAlchemyJobRepository(db.session_factory)
            if await repo.get(job_id) is None:
                raise HTTPException(status_code=404, detail="job not found")
            await repo.save_processing_settings(job_id, payload)
            return {
                "job_id": str(job_id),
                "processing_settings": payload.model_dump(mode="json"),
            }
        finally:
            await db.dispose()

    return app


app = create_api()


def main():
    import uvicorn

    uvicorn.run(
        "ai_gif_studio.interfaces.api:app",
        host="0.0.0.0",
        port=8000,
    )
