from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ai_gif_studio.domain.probe_errors import (
    ProbeCorruptMediaError,
    ProbeExecutionError,
    ProbeFileNotFoundError,
    ProbeResourceLimitError,
    ProbeTimeoutError,
)
from ai_gif_studio.quality_engine import QualityEngine

pytestmark = pytest.mark.unit


class _Probe:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def probe(self, path: Path, *, count_frames: bool = False) -> dict:
        raise self.error


def _engine_raising(error: BaseException) -> QualityEngine:
    return QualityEngine()


@pytest.mark.parametrize(
    "error_type",
    [
        ProbeFileNotFoundError,
        ProbeCorruptMediaError,
        ProbeTimeoutError,
        ProbeResourceLimitError,
        ProbeExecutionError,
    ],
)
@pytest.mark.asyncio
async def test_expected_probe_errors_are_contained(
    tmp_path: Path, error_type: type[Exception]
) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"gif")
    engine = _engine_raising(error_type("boom"))

    report = await engine.inspect(path, _Probe(error_type("boom")), max_bytes=100)

    assert report.valid is False
    assert report.checks == (f"probe:{error_type.__name__}",)


@pytest.mark.parametrize(
    "error_type",
    [TypeError, KeyError, AttributeError, ValueError, ArithmeticError],
)
@pytest.mark.asyncio
async def test_unexpected_probe_errors_propagate(
    tmp_path: Path, error_type: type[Exception]
) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"gif")
    engine = _engine_raising(error_type("bug"))

    with pytest.raises(error_type):
        await engine.inspect(path, _Probe(error_type("bug")), max_bytes=100)


@pytest.mark.asyncio
async def test_cancellation_propagates(tmp_path: Path) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"gif")
    engine = _engine_raising(asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await engine.inspect(
            path,
            _Probe(asyncio.CancelledError()),
            max_bytes=100,
        )


@pytest.mark.asyncio
async def test_environment_error_propagates(tmp_path: Path) -> None:
    path = tmp_path / "output.gif"
    path.write_bytes(b"gif")
    engine = _engine_raising(RuntimeError("ffprobe binary not found"))

    with pytest.raises(RuntimeError):
        await engine.inspect(
            path,
            _Probe(RuntimeError("ffprobe binary not found")),
            max_bytes=100,
        )
