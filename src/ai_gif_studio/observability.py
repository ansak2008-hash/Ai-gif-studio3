from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import logging
import time
from uuid import UUID

from __future__ import annotations
logger = logging.getLogger("ai_gif_studio.observability")


def _emit(event: str, *, job_id: UUID | str | None = None, **fields: object) -> None:
    payload = {"event": event, **fields}
    if job_id is not None:
        payload["job_id"] = str(job_id)
    logger.info(json.dumps(payload, separators=(",", ":"), default=str))


@asynccontextmanager
async def stage(job_id: UUID | str, name: str) -> AsyncIterator[None]:
    started = time.perf_counter()
    _emit("stage_started", job_id=job_id, stage=name)
    try:
        yield
    except Exception as exc:
        _emit("stage_failed", job_id=job_id, stage=name, duration_ms=round((time.perf_counter() - started) * 1000), error=type(exc).__name__)
        raise
    else:
        _emit("stage_completed", job_id=job_id, stage=name, duration_ms=round((time.perf_counter() - started) * 1000))
