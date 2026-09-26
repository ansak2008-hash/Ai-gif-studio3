from __future__ import annotations

from uuid import UUID, uuid4

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai_gif_studio.application.capabilities import CAPABILITIES
from ai_gif_studio.configuration import AppSettings, get_settings
from ai_gif_studio.database import Database
from ai_gif_studio.database.repositories import SqlAlchemyJobRepository
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.presets import build_design_spec, list_presets


def create_api(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AI Creative GIF Studio", version="0.3.0")

    async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if not settings.api_key:
            if settings.environment == "production":
                raise HTTPException(status_code=503, detail="API authentication is not configured")
            return
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        db_engine = create_async_engine(settings.database_url)
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            async with db_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await redis.ping()
        finally:
            await redis.close()
            await db_engine.dispose()
        return {"status": "ready"}

    @app.get("/v1/presets", dependencies=[Depends(require_api_key)])
    async def presets():
        return {"presets": [{"name": name, "design_spec": build_design_spec(name).model_dump(mode="json")} for name in list_presets()]}

    @app.get("/v1/presets/{name}", dependencies=[Depends(require_api_key)])
    async def preset(name: str):
        try:
            return {"name": name, "design_spec": build_design_spec(name).model_dump(mode="json")}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.put("/v1/jobs/{job_id}/preset/{name}", dependencies=[Depends(require_api_key)])
    async def apply_preset(job_id: UUID, name: str):
        db = Database(settings.database_url)
        try:
            repo = SqlAlchemyJobRepository(db.session_factory)
            if await repo.get(job_id) is None:
                raise HTTPException(status_code=404, detail="job not found")
            try:
                spec = build_design_spec(name)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            await repo.save_design_spec(job_id, spec)
            return {"job_id": str(job_id), "preset": name, "design_spec": spec.model_dump(mode="json")}
        finally:
            await db.dispose()

    @app.get("/v1/capabilities", dependencies=[Depends(require_api_key)])
    async def capabilities():
        return {key: {"state": value.state, "requirements": value.requirements} for key, value in CAPABILITIES.items()}

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
                "processing_settings": (await repo.get_processing_settings(job.id)).model_dump(mode="json"),
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
            return {"job_id": str(job_id), "processing_settings": payload.model_dump(mode="json")}
        finally:
            await db.dispose()

    return app


app = create_api()


def main():
    import uvicorn
    uvicorn.run("ai_gif_studio.interfaces.api:app", host="0.0.0.0", port=8000)
