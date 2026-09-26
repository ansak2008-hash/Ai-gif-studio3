from pathlib import Path

import pytest

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.design_production2 import ProductionDesignGifEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService


@pytest.mark.integration
@pytest.mark.parametrize("size", ["540x960", "960x720", "720x720"])
async def test_supported_aspects_render_valid_320_gif(tmp_path: Path, size: str):
    ffmpeg = FFmpegService(timeout=30)
    source = tmp_path / f"source-{size}.mp4"
    target = tmp_path / f"output-{size}.gif"

    await ffmpeg.run(
        [
            "-f", "lavfi",
            "-i", f"color=c=black:s={size}:r=20:d=1",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
        ]
    )

    engine = ProductionDesignGifEngine(ffmpeg, RenderConfiguration())
    settings = ProcessingSettings(fps=20, max_duration_seconds=1.0)
    await engine.convert(source, target, DesignSpec(), settings)

    report = await engine.quality.inspect(
        target,
        ffmpeg,
        settings.max_bytes,
        selected_fps=20,
        expected_duration=1.0,
    )
    assert report.valid
    assert (report.width, report.height) == (320, 320)
    assert report.frames >= 1
