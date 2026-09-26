"""True 1:1 crop and high-quality GIF encoding, without design effects."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .config import CropOnlyConfiguration


class CropOnlyError(RuntimeError):
    """Raised when a source cannot be converted within Crop Only constraints."""


@dataclass(frozen=True, slots=True)
class CropOnlyResult:
    output_path: Path
    duration_seconds: float
    start_seconds: float
    fps: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class _VideoInfo:
    duration_seconds: float
    width: int
    height: int


Run = Callable[..., subprocess.CompletedProcess[str]]


def crop_video_to_gif(
    input_path: str | Path,
    output_path: str | Path,
    *,
    configuration: CropOnlyConfiguration | None = None,
    ffmpeg_binary: str = "ffmpeg",
    ffprobe_binary: str = "ffprobe",
    runner: Run = subprocess.run,
) -> CropOnlyResult:
    """Convert a video into a 320×320 GIF using only a real centered crop.

    For every aspect ratio, the largest source square is retained: wide video
    loses equal amounts from left and right, tall video loses equal amounts
    from top and bottom.  This centre-preserving strategy maximises retained
    pixels and keeps a typical primary subject in view without stretching or
    adding backgrounds.  A video longer than six seconds uses its temporal
    centre, avoiding a bias toward intros or outros.

    The function leaves ``output_path`` untouched unless an FPS ladder attempt
    satisfies ``max_output_bytes``.  ``runner`` is injectable for integration
    tests; callers normally use the default subprocess runner.
    """
    config = configuration or CropOnlyConfiguration()
    source, destination = Path(input_path), Path(output_path)
    if not source.is_file():
        raise CropOnlyError(f"Input video does not exist: {source}")
    if source.resolve() == destination.resolve():
        raise CropOnlyError("input_path and output_path must differ")

    info = _probe_video(source, ffprobe_binary, runner)
    duration = min(info.duration_seconds, config.default_duration_seconds)
    start = max(0.0, (info.duration_seconds - duration) / 2)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="crop-only-") as temporary:
        workdir = Path(temporary)
        for fps in config.fps_ladder:
            candidate = workdir / f"crop-{fps}.gif"
            command = _ffmpeg_command(
                ffmpeg_binary, source, candidate, start, duration, fps, config
            )
            _run(command, runner, "FFmpeg conversion failed")
            if not candidate.is_file():
                raise CropOnlyError("FFmpeg reported success but produced no GIF")
            size = candidate.stat().st_size
            if size <= config.max_output_bytes:
                # replace is atomic when both paths reside in destination.parent.
                staged = destination.parent / f".{destination.name}.crop-only.tmp"
                shutil.copyfile(candidate, staged)
                os.replace(staged, destination)
                return CropOnlyResult(destination, duration, start, fps, size)

    raise CropOnlyError(
        f"GIF exceeds {config.max_output_bytes} bytes at every configured FPS"
    )


def _probe_video(path: Path, binary: str, runner: Run) -> _VideoInfo:
    completed = _run(
        [binary, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(path)],
        runner,
        "FFprobe failed",
    )
    try:
        data = json.loads(completed.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise CropOnlyError("Could not read video dimensions or duration") from error
    if duration <= 0 or width <= 0 or height <= 0:
        raise CropOnlyError("Video must have a positive duration and dimensions")
    return _VideoInfo(duration, width, height)


def _ffmpeg_command(
    binary: str, source: Path, target: Path, start: float, duration: float,
    fps: int, config: CropOnlyConfiguration,
) -> list[str]:
    # crop=min(iw,ih) retains the largest possible square for any aspect ratio.
    # crop/scale precede fps: image resampling is completed at high quality before
    # temporal reduction. palettegen/use provides GIF's indexed palette without
    # producing lossy intermediate image frames.
    filters = (
        f"[0:v]crop='min(iw,ih)':'min(iw,ih)':'(iw-min(iw,ih))/2':'(ih-min(iw,ih))/2',"
        f"scale={config.output_size}:{config.output_size}:flags=lanczos,"
        f"fps={fps},format=rgb24,split[a][b];"
        f"[a]palettegen=max_colors={config.palette_colors}:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle[v]"
    )
    return [
        binary, "-hide_banner", "-loglevel", "error", "-hwaccel", "none", "-i", str(source),
        "-ss", f"{start:.6f}", "-t", f"{duration:.6f}", "-filter_complex", filters,
        "-map", "[v]", "-an", "-loop", "0", "-y", str(target),
    ]


def _run(command: Sequence[str], runner: Run, description: str) -> subprocess.CompletedProcess[str]:
    try:
        completed = runner(command, check=False, capture_output=True, text=True)
    except OSError as error:
        raise CropOnlyError(f"{description}: {error}") from error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise CropOnlyError(f"{description}: {detail}")
    return completed
