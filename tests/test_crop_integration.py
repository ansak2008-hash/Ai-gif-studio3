from pathlib import Path
import shutil
import subprocess

import pytest

from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.engines.crop import CropOnlyEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService


@pytest.mark.asyncio
async def test_real_video_to_gif(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg unavailable")
    src = tmp_path / "in.mp4"
    out = tmp_path / "out.gif"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-f", "lavfi",
            "-i", "testsrc=size=640x360:rate=15", "-t", "1",
            "-pix_fmt", "yuv420p", str(src),
        ],
        check=True,
    )
    await CropOnlyEngine(FFmpegService(timeout=60)).convert(
        src, out, ProcessingSettings(max_duration_seconds=1, fps=8)
    )
    assert out.exists() and out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
