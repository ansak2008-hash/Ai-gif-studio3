"""Twenty-job concurrency smoke/load test for the real media pipeline.

Run with: pytest -q tests/load_test.py -m slow
It creates one tiny synthetic MP4, then executes the real probe/render/quality/
artifact/delivery-shaped stages concurrently. Telegram delivery is represented by
an isolated local sink because the test must not require production credentials.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService
from ai_gif_studio.observability import stage
from ai_gif_studio.quality_engine import QualityEngine


@pytest.mark.slow
@pytest.mark.integration
async def test_twenty_concurrent_media_jobs(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe unavailable")

    source = tmp_path / "source.mp4"
    generator = FFmpegService(ffmpeg, ffprobe, timeout=60)
    await generator.run([
        "-f", "lavfi", "-i", "color=c=black:s=320x320:r=8",
        "-t", "1", "-pix_fmt", "yuv420p", str(source),
    ])

    settings = ProcessingSettings(fps=8, max_duration_seconds=1.0, max_bytes=2_400_000)
    engine = CropOnlyEngine(generator)
    quality = QualityEngine()
    root = tmp_path / "jobs"
    semaphore = asyncio.Semaphore(20)

    async def one(index: int) -> None:
        async with semaphore:
            job_id = f"load-{index:02d}"
            job_dir = root / job_id
            job_dir.mkdir(parents=True)
            target = job_dir / "output.gif"
            async with stage(job_id, "download"):
                shutil.copyfile(source, job_dir / "input.mp4")
            async with stage(job_id, "probe"):
                await generator.probe(job_dir / "input.mp4")
            async with stage(job_id, "render"):
                await engine.convert(job_dir / "input.mp4", target, settings)
            async with stage(job_id, "quality"):
                report = await quality.inspect(target, generator, settings.max_bytes, selected_fps=settings.fps, expected_duration=1.0)
                assert report.valid, report
            async with stage(job_id, "artifact_register"):
                assert target.is_file() and target.stat().st_size > 0
            async with stage(job_id, "delivery"):
                delivery_sink = job_dir / "delivered.gif"
                shutil.copyfile(target, delivery_sink)
                assert delivery_sink.is_file()

    await asyncio.gather(*(one(i) for i in range(20)))
