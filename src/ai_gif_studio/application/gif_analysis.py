from __future__ import annotations

import io
import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, UnidentifiedImageError

ANALYSIS_SCHEMA_VERSION = 1
DEFAULT_MAX_INPUT_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_CANVAS_PIXELS = 16_777_216
DEFAULT_MAX_DECODED_FRAMES = 1_000
DEFAULT_MAX_TOTAL_PIXELS = 100_000_000
_URL_READ_CHUNK_BYTES = 64 * 1024


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
    motion_p25: float
    motion_p50: float
    motion_p75: float
    motion_p90: float
    motion_p95: float
    motion_p99: float
    first_last_difference: float
    corner_color: tuple[int, int, int]
    corner_color_is_heuristic: bool
    frame_palette_colors: tuple[int, ...]
    max_palette_colors: int
    duration_min_ms: int
    duration_max_ms: int
    duration_histogram: tuple[tuple[int, int], ...]
    timing_is_uniform: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def _validate_limits(
    *,
    max_input_bytes: int,
    max_canvas_pixels: int,
    max_decoded_frames: int,
    max_total_pixels: int,
) -> None:
    limits = {
        "max_input_bytes": max_input_bytes,
        "max_canvas_pixels": max_canvas_pixels,
        "max_decoded_frames": max_decoded_frames,
        "max_total_pixels": max_total_pixels,
    }
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in limits.values()):
        raise GifAnalysisError("resource limits must be positive integers")


def _open_gif(payload: bytes, *, max_canvas_pixels: int) -> Image.Image:
    if not isinstance(payload, bytes):
        raise GifAnalysisError("input must be bytes")
    if not payload:
        raise GifAnalysisError("input is empty")
    try:
        image = Image.open(io.BytesIO(payload))
    except (UnidentifiedImageError, OSError) as exc:
        raise GifAnalysisError("input is not a valid GIF") from exc
    if image.format != "GIF":
        image.close()
        raise GifAnalysisError("input format must be GIF")
    width, height = image.size
    if width <= 0 or height <= 0:
        image.close()
        raise GifAnalysisError("GIF canvas dimensions must be positive")
    if width * height > max_canvas_pixels:
        image.close()
        raise GifAnalysisError("GIF canvas exceeds configured pixel limit")
    return image


def _decode_frames(
    payload: bytes,
    *,
    max_canvas_pixels: int,
    max_decoded_frames: int,
    max_total_pixels: int,
) -> tuple[
    tuple[Image.Image, ...],
    tuple[int, ...],
    int | None,
]:
    image = _open_gif(payload, max_canvas_pixels=max_canvas_pixels)
    frames: list[Image.Image] = []
    durations: list[int] = []
    total_pixels = 0
    loop_count = image.info.get("loop")
    try:
        while True:
            if len(frames) >= max_decoded_frames:
                raise GifAnalysisError("GIF exceeds configured frame limit")
            duration = image.info.get("duration", 0)
            if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
                raise GifAnalysisError("GIF frame duration must be positive")
            frame = image.convert("RGB").copy()
            total_pixels += frame.width * frame.height
            if total_pixels > max_total_pixels:
                frame.close()
                raise GifAnalysisError("GIF exceeds configured decoded pixel budget")
            frames.append(frame)
            durations.append(duration)
            image.seek(image.tell() + 1)
    except EOFError:
        pass
    except GifAnalysisError:
        raise
    except (OSError, ValueError) as exc:
        raise GifAnalysisError("GIF frame decoding failed") from exc
    finally:
        image.close()
    if not frames:
        raise GifAnalysisError("GIF contains no frames")
    return tuple(frames), tuple(durations), loop_count if isinstance(loop_count, int) else None


def _palette_size(frame: Image.Image) -> int:
    colors = frame.getcolors(maxcolors=frame.width * frame.height)
    if colors is None:
        raise GifAnalysisError("decoded frame palette cardinality could not be determined")
    return len(colors)


def _percentile_values(values: list[float]) -> tuple[float, float, float, float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    percentiles = np.percentile(values, [25, 50, 75, 90, 95, 99])
    return tuple(float(value) for value in percentiles)


def _duration_histogram(durations: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for duration in durations:
        counts[duration] = counts.get(duration, 0) + 1
    return tuple(sorted(counts.items()))


def analyze_gif_bytes(
    payload: bytes,
    *,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_canvas_pixels: int = DEFAULT_MAX_CANVAS_PIXELS,
    max_decoded_frames: int = DEFAULT_MAX_DECODED_FRAMES,
    max_total_pixels: int = DEFAULT_MAX_TOTAL_PIXELS,
) -> GifAnalysisReport:
    _validate_limits(
        max_input_bytes=max_input_bytes,
        max_canvas_pixels=max_canvas_pixels,
        max_decoded_frames=max_decoded_frames,
        max_total_pixels=max_total_pixels,
    )
    if not isinstance(payload, bytes):
        raise GifAnalysisError("input must be bytes")
    if len(payload) > max_input_bytes:
        raise GifAnalysisError("input exceeds configured size limit")
    frames, durations, loop_count = _decode_frames(
        payload,
        max_canvas_pixels=max_canvas_pixels,
        max_decoded_frames=max_decoded_frames,
        max_total_pixels=max_total_pixels,
    )
    first = frames[0]
    previous = first
    motions: list[float] = []
    palette_sizes: list[int] = []
    try:
        for frame in frames:
            palette_sizes.append(_palette_size(frame))
            if frame is not first:
                previous_array = np.asarray(previous, dtype=np.int16)
                current_array = np.asarray(frame, dtype=np.int16)
                motions.append(float(np.abs(current_array - previous_array).mean()))
                previous = frame
        first_array = np.asarray(first, dtype=np.int16)
        last_array = np.asarray(frames[-1], dtype=np.int16)
        first_last = float(np.abs(first_array - last_array).mean())
        corner_points = (
            first.getpixel((0, 0)),
            first.getpixel((first.width - 1, 0)),
            first.getpixel((0, first.height - 1)),
            first.getpixel((first.width - 1, first.height - 1)),
        )
    finally:
        for frame in frames:
            frame.close()
    corner_color = tuple(
        round(sum(point[channel] for point in corner_points) / 4) for channel in range(3)
    )
    motion_percentiles = _percentile_values(motions)
    duration_ms = sum(durations)
    mean_duration = duration_ms / len(durations)
    return GifAnalysisReport(
        schema_version=ANALYSIS_SCHEMA_VERSION,
        width=first.width,
        height=first.height,
        frame_count=len(frames),
        duration_ms=duration_ms,
        effective_fps=1000.0 / mean_duration,
        file_size_bytes=len(payload),
        loop_count=loop_count,
        frame_motion=tuple(motions),
        motion_mean=float(np.mean(motions)) if motions else 0.0,
        motion_max=float(np.max(motions)) if motions else 0.0,
        motion_p25=motion_percentiles[0],
        motion_p50=motion_percentiles[1],
        motion_p75=motion_percentiles[2],
        motion_p90=motion_percentiles[3],
        motion_p95=motion_percentiles[4],
        motion_p99=motion_percentiles[5],
        first_last_difference=first_last,
        corner_color=corner_color,
        corner_color_is_heuristic=True,
        frame_palette_colors=tuple(palette_sizes),
        max_palette_colors=max(palette_sizes),
        duration_min_ms=min(durations),
        duration_max_ms=max(durations),
        duration_histogram=_duration_histogram(durations),
        timing_is_uniform=len(set(durations)) == 1,
    )


def analyze_gif_url(
    url: str,
    *,
    timeout_seconds: float = 20.0,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_canvas_pixels: int = DEFAULT_MAX_CANVAS_PIXELS,
    max_decoded_frames: int = DEFAULT_MAX_DECODED_FRAMES,
    max_total_pixels: int = DEFAULT_MAX_TOTAL_PIXELS,
) -> GifAnalysisReport:
    _validate_limits(
        max_input_bytes=max_input_bytes,
        max_canvas_pixels=max_canvas_pixels,
        max_decoded_frames=max_decoded_frames,
        max_total_pixels=max_total_pixels,
    )
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise GifAnalysisError("URL must use HTTP or HTTPS")
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
        raise GifAnalysisError("timeout_seconds must be positive")
    request = Request(url, headers={"User-Agent": "AiGifStudio-GifAnalysis/1"})
    chunks: list[bytes] = []
    total = 0
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise GifAnalysisError("invalid Content-Length header") from exc
                if declared_length > max_input_bytes:
                    raise GifAnalysisError("response exceeds configured size limit")
            while True:
                chunk = response.read(min(_URL_READ_CHUNK_BYTES, max_input_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_input_bytes:
                    raise GifAnalysisError("response exceeds configured size limit")
                chunks.append(chunk)
    except GifAnalysisError:
        raise
    except (OSError, ValueError) as exc:
        raise GifAnalysisError("GIF URL retrieval failed") from exc
    return analyze_gif_bytes(
        b"".join(chunks),
        max_input_bytes=max_input_bytes,
        max_canvas_pixels=max_canvas_pixels,
        max_decoded_frames=max_decoded_frames,
        max_total_pixels=max_total_pixels,
    )
