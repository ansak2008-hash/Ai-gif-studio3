from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ai_gif_studio.interfaces import api


@pytest.mark.unit
async def test_health_is_process_liveness_only() -> None:
    application = api.create_api()
    health = next(route.endpoint for route in application.routes if route.path == "/health")
    assert await health() == {"status": "ok"}


@pytest.mark.unit
async def test_readiness_reports_all_dependencies(monkeypatch) -> None:
    settings = SimpleNamespace(
        database_url="sqlite+aiosqlite:///unused.db",
        redis_url="redis://unused",
        ffmpeg_binary="ffmpeg",
    )

    async def healthy(_):
        return True

    monkeypatch.setattr(api, "_check_database", healthy)
    monkeypatch.setattr(api, "_check_redis", healthy)
    monkeypatch.setattr(api, "_check_ffmpeg", healthy)

    checks = await api._readiness_checks(settings)
    assert checks == {"database": True, "redis": True, "ffmpeg": True}


@pytest.mark.unit
async def test_readiness_fails_closed_when_dependency_is_unavailable(monkeypatch) -> None:
    settings = SimpleNamespace(
        database_url="sqlite+aiosqlite:///unused.db",
        redis_url="redis://unused",
        ffmpeg_binary="ffmpeg",
    )

    async def healthy(_):
        return True

    async def unavailable(_):
        return False

    monkeypatch.setattr(api, "_check_database", healthy)
    monkeypatch.setattr(api, "_check_redis", unavailable)
    monkeypatch.setattr(api, "_check_ffmpeg", healthy)

    application = api.create_api(settings)
    ready = next(route.endpoint for route in application.routes if route.path == "/ready")

    with pytest.raises(HTTPException) as error:
        await ready()

    assert error.value.status_code == 503
    assert error.value.detail == {
        "status": "not_ready",
        "checks": {"database": True, "redis": False, "ffmpeg": True},
    }
