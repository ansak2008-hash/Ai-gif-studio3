import shutil
import subprocess
from pathlib import Path

import pytest

from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.engines.design import DesignGifEngine
from ai_gif_studio.infrastructure.ffmpeg import FFmpegService


@pytest.mark.asyncio
async def test_design_gif_real_pipeline(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg unavailable")
    src = tmp_path / "in.mp4"
    out = tmp_path / "out.gif"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-f", "lavfi",
            "-i", "testsrc=size=640x360:rate=10", "-t", "1",
            "-pix_fmt", "yuv420p", str(src),
        ],
        check=True,
    )
    design = DesignSpec(
        crop={"mode": "smart", "focus": {"x": 0.8, "y": 0.5}, "anchor": "center"},
        background={"mode": "solid", "color": "#101820"},
        frame={"style": "rounded", "radius": 24, "color": "#ffffff"},
    )
    await DesignGifEngine(FFmpegService(timeout=60)).convert(
        src, out, design, ProcessingSettings(max_duration_seconds=1, fps=8)
    )
    assert out.exists()
    assert out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
    assert out.stat().st_size <= 2_400_000


@pytest.mark.asyncio
async def test_design_gif_rejects_invalid_background(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg unavailable")
    src = tmp_path / "in.mp4"
    out = tmp_path / "out.gif"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-f", "lavfi",
            "-i", "testsrc=size=320x320:rate=8", "-t", "0.5",
            "-pix_fmt", "yuv420p", str(src),
        ],
        check=True,
    )
    with pytest.raises(ValueError, match="background color"):
        await DesignGifEngine(FFmpegService(timeout=30)).convert(
            src, out,
            DesignSpec(background={"mode": "solid", "color": "invalid"}),
            ProcessingSettings(max_duration_seconds=0.5, fps=8),
        )


@pytest.mark.asyncio
async def test_design_motion_layers_and_text(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg unavailable")
    src = tmp_path / "in.mp4"
    out = tmp_path / "out.gif"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
         "testsrc=size=640x360:rate=10", "-t", "0.7", "-pix_fmt", "yuv420p", str(src)],
        check=True,
    )
    design = DesignSpec(
        motion={"style": "float", "amount": 0.08},
        layers=[{"type": "border", "thickness": 3, "color": "#ffffff", "opacity": 0.7}],
        text={"enabled": True, "content": "AI GIF", "size": 20, "x": 12, "y": 280},
    )
    await DesignGifEngine(FFmpegService(timeout=60)).convert(
        src, out, design, ProcessingSettings(max_duration_seconds=0.7, fps=8)
    )
    assert out.exists()
    assert out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
