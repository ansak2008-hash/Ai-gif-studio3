from __future__ import annotations

from pathlib import Path

import pytest

from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine


pytestmark = pytest.mark.unit


class _FakeFFmpeg:
    def __init__(self) -> None:
        self.runs: list[list[str]] = []

    async def probe(self, _source: Path):
        return {
            "streams": [{"codec_type": "video"}],
            "format": {"duration": 6.0},
        }

    async def run(self, argv: list[str]) -> None:
        self.runs.append(argv)
        Path(argv[-1]).write_bytes(b"GIF89a")


def _fps_values(ffmpeg: _FakeFFmpeg) -> list[int]:
    return [
        int(argument.split("=", 1)[1].split(",", 1)[0])
        for run in ffmpeg.runs
        if "-vf" in run
        for argument in [run[run.index("-vf") + 1]]
    ]


@pytest.mark.asyncio
async def test_crop_engine_uses_canonical_fps_ladder() -> None:
    ffmpeg = _FakeFFmpeg()
    engine = CropOnlyEngine(ffmpeg)
    source = Path("source.mp4")
    target = Path("output.gif")

    result = await engine.convert(source, target, ProcessingSettings(fps=20))

    assert result == target
    assert _fps_values(ffmpeg) == [20, 18, 15]
    target.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_crop_engine_preserves_explicit_non_ladder_fps() -> None:
    ffmpeg = _FakeFFmpeg()
    engine = CropOnlyEngine(ffmpeg)
    source = Path("source.mp4")
    target = Path("output.gif")

    result = await engine.convert(source, target, ProcessingSettings(fps=19))

    assert result == target
    assert _fps_values(ffmpeg) == [19, 18, 15]
    target.unlink(missing_ok=True)
