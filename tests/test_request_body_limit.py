from __future__ import annotations

import pytest

from ai_gif_studio.interfaces.api import RequestBodyLimitMiddleware


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_body_limit_rejects_chunked_body_without_content_length() -> None:
    received = False
    responses: list[dict] = []

    async def app(scope, receive, send) -> None:
        nonlocal received
        received = True
        await receive()

    messages = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    async def send(message):
        responses.append(message)

    middleware = RequestBodyLimitMiddleware(app, max_bytes=4)
    await middleware({"type": "http", "method": "POST", "path": "/"}, receive, send)

    assert not received
    assert responses[0]["status"] == 413
