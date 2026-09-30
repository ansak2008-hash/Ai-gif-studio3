from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaPreflightError(ValueError):
    """Input media cannot safely enter the production pipeline."""


@dataclass(frozen=True, slots=True)
class MediaPreflightResult:
    probe: dict[str, Any]
    width: int
    height: int
    duration_seconds: float
    fps: float
    frame_count: int


async def preflight_media(
    source: Path,
    ffmpeg,
    *,
    max_bytes: int | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    max_duration_seconds: float | None = None,
) -> MediaPreflightResult:
    if not source.is_file():
        raise MediaPreflightError("input file does not exist")
    size = source.stat().st_size
    if size <= 0:
        raise MediaPreflightError("input file is empty")
    if max_bytes is not None and size > max_bytes:
        raise MediaPreflightError("input file exceeds the configured size limit")

    try:
        probe = await ffmpeg.probe(source, count_frames=True)
    except Exception as exc:
        raise MediaPreflightError("input media could not be probed") from exc

    video = next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), None)
    if video is None:
        raise MediaPreflightError("input has no video stream")

    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise MediaPreflightError("input video has invalid dimensions")
    if max_width is not None and width > max_width:
        raise MediaPreflightError("input video width exceeds the configured limit")
    if max_height is not None and height > max_height:
        raise MediaPreflightError("input video height exceeds the configured limit")

    frame_count = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    if frame_count <= 0:
        raise MediaPreflightError("input video has no readable frames")

    rate = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    try:
        numerator, denominator = rate.split("/", 1)
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    if fps <= 0:
        raise MediaPreflightError("input video has invalid frame rate")

    try:
        duration = float(probe.get("format", {}).get("duration") or video.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        raise MediaPreflightError("input video has invalid duration")
    if max_duration_seconds is not None and duration > max_duration_seconds:
        raise MediaPreflightError("input video duration exceeds the configured limit")

    return MediaPreflightResult(
        probe=probe,
        width=width,
        height=height,
        duration_seconds=duration,
        fps=fps,
        frame_count=frame_count,
    )
