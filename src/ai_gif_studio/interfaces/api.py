from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai_gif_studio.configuration import AppSettings, get_settings


def create_api(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AI Creative GIF Studio")

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

    return app


app = create_api()


def main():
    import uvicorn

    uvicorn.run("ai_gif_studio.interfaces.api:app", host="0.0.0.0", port=8000)
