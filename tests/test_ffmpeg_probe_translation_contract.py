from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ai_gif_studio.domain.probe_errors import (
    ProbeCorruptMediaError,
    ProbeError,
    ProbeExecutionError,
    ProbeTimeoutError,
)
from ai_gif_studio.infrastructure.ffmpeg import (
    FFmpegCommandError,
    FFmpegService,
    FFmpegTimeoutError,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_timeout_translates_to_probe_timeout() -> None:
    service = FFmpegService()
    service._run = _async_raiser(FFmpegTimeoutError("timeout"))
    with pytest.raises(ProbeTimeoutError):
        await service.probe(Path("input.mp4"))


@pytest.mark.asyncio
async def test_nonzero_exit_translates_to_probe_execution() -> None:
    service = FFmpegService()
    service._run = _async_raiser(FFmpegCommandError("ffprobe failed"))
    with pytest.raises(ProbeExecutionError):
        await service.probe(Path("input.mp4"))


@pytest.mark.asyncio
async def test_invalid_json_translates_to_probe_corrupt_media() -> None:
    service = FFmpegService()
    service._run = _async_return((b"not-json", b""))
    with pytest.raises(ProbeCorruptMediaError):
        await service.probe(Path("input.mp4"))


@pytest.mark.asyncio
async def test_missing_binary_is_not_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    async def missing_binary(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", missing_binary)
    service = FFmpegService(ffprobe="missing-ffprobe-binary")
    with pytest.raises(FileNotFoundError) as exc_info:
        await service.probe(Path("input.mp4"))
    assert not isinstance(exc_info.value, ProbeError)


@pytest.mark.asyncio
async def test_internal_key_error_is_not_translated() -> None:
    service = FFmpegService()
    service._run = _async_raiser(KeyError("internal parser bug"))
    with pytest.raises(KeyError):
        await service.probe(Path("input.mp4"))


@pytest.mark.asyncio
async def test_internal_value_error_is_not_translated() -> None:
    service = FFmpegService()
    service._run = _async_raiser(ValueError("internal parser bug"))
    with pytest.raises(ValueError):
        await service.probe(Path("input.mp4"))


def _async_raiser(error: BaseException):
    async def raise_error(*args, **kwargs):
        raise error

    return raise_error


def _async_return(value):
    async def return_value(*args, **kwargs):
        return value

    return return_value
