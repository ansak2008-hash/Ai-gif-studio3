from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, UnidentifiedImageError

ANALYSIS_SCHEMA_VERSION = 1


class GifAnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class GifAnalysisReport:
    schema_version: int
    width: int
    height: int
    frame_count: int
    duration_ms: int
    effective_fps: float
    file_size_bytes: int
    loop_count: int | None
    frame_motion: tuple[float, ...]
    motion_mean: float
    motion_max: float
    first_last_difference: float
    corner_color: tuple[int, int, int]
    corner_color_is_heuristic: bool
    max_palette_colors: int
    duration_min_ms: int
    duration_max_ms: int
    timing_is_uniform: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def _decode(payload: bytes) -> tuple[Image.Image, list[int]]:
    if not payload:
        raise GifAnalysisError("input is empty")
    try:
        image = Image.open(io.BytesIO(payload))
    except (UnidentifiedImageError, OSError) as exc:
        raise GifAnalysisError("input is not a valid GIF") from exc
    if image.format != "GIF":
        raise GifAnalysisError("input format must be GIF")
    frames: list[Image.Image] = []
    durations: list[int] = []
    try:
        while True:
            duration = image.info.get("duration", 0)
            if not isinstance(duration, int) or duration <= 0:
                raise GifAnalysisError("GIF frame duration must be positive")
            frames.append(image.convert("RGB").copy())
            durations.append(duration)
            image.seek(image.tell() + 1)
    except EOFError:
        pass
    except (OSError, ValueError) as exc:
        raise GifAnalysisError("GIF frame decoding failed") from exc
    if not frames:
        raise GifAnalysisError("GIF contains no frames")
    return frames, durations


def analyze_gif_bytes(payload: bytes, *, max_input_bytes: int = 20 * 1024 * 1024) -> GifAnalysisReport:
    if len(payload) > max_input_bytes:
        raise GifAnalysisError("input exceeds configured size limit")
    frames, durations = _decode(payload)
    arrays = [np.asarray(frame, dtype=np.int16) for frame in frames]
    motions = [
        float(np.abs(arrays[index] - arrays[index - 1]).mean())
        for index in range(1, len(arrays))
    ]
    first_last = 0.0 if len(arrays) == 1 else float(np.abs(arrays[0] - arrays[-1]).mean())
    corner_points = (
        frames[0].getpixel((0, 0)),
        frames[0].getpixel((frames[0].width - 1, 0)),
        frames[0].getpixel((0, frames[0].height - 1)),
        frames[0].getpixel((frames[0].width - 1, frames[0].height - 1)),
    )
    corner_color = tuple(round(sum(point[channel] for point in corner_points) / 4) for channel in range(3))
    palette_sizes = [len(frame.getcolors(maxcolors=1_000_000) or ()) for frame in frames]
    duration_ms = sum(durations)
    mean_duration = duration_ms / len(durations)
    loop_count = frames[0].info.get("loop")
    return GifAnalysisReport(
        schema_version=ANALYSIS_SCHEMA_VERSION,
        width=frames[0].width,
        height=frames[0].height,
        frame_count=len(frames),
        duration_ms=duration_ms,
        effective_fps=1000.0 / mean_duration,
        file_size_bytes=len(payload),
        loop_count=loop_count if isinstance(loop_count, int) else None,
        frame_motion=tuple(motions),
        motion_mean=float(np.mean(motions)) if motions else 0.0,
        motion_max=float(np.max(motions)) if motions else 0.0,
        first_last_difference=first_last,
        corner_color=corner_color,
        corner_color_is_heuristic=True,
        max_palette_colors=max(palette_sizes),
        duration_min_ms=min(durations),
        duration_max_ms=max(durations),
        timing_is_uniform=len(set(durations)) == 1,
    )


def analyze_gif_url(
    url: str,
    *,
    timeout_seconds: float = 20.0,
    max_input_bytes: int = 20 * 1024 * 1024,
) -> GifAnalysisReport:
    if not url.startswith(("http://", "https://")):
        raise GifAnalysisError("URL must use HTTP or HTTPS")
    request = Request(url, headers={"User-Agent": "AiGifStudio-GifAnalysis/1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read(max_input_bytes + 1)
    return analyze_gif_bytes(payload, max_input_bytes=max_input_bytes)
