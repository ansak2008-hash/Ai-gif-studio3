from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ai_gif_studio.configuration.render import DEFAULT_FPS_LADDER


@dataclass(frozen=True, slots=True)
class QualityReport:
    valid: bool
    size_bytes: int
    width: int
    height: int
    duration_seconds: float
    fps: float
    frames: int
    size_ratio: float
    selected_fps: int
    checks: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


class QualityEngine:
    def ladder(
        self,
        preferred: int,
        current_size: int | None = None,
        max_bytes: int = 2_400_000,
    ) -> tuple[int, ...]:
        del current_size, max_bytes
        lower_or_equal = tuple(fps for fps in DEFAULT_FPS_LADDER if fps <= preferred)
        if lower_or_equal:
            return lower_or_equal
        return (preferred,)

    async def inspect(
        self,
        path: Path,
        ffmpeg,
        max_bytes: int,
        expected_width: int = 320,
        expected_height: int = 320,
        selected_fps: int = 30,
        expected_duration: float | None = 6.0,
        duration_tolerance: float = 0.35,
        min_frames: int = 1,
    ) -> QualityReport:
        if not path.is_file():
            return QualityReport(False, 0, 0, 0, 0.0, 0.0, 0, 1.0, selected_fps, ("missing",))
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            return QualityReport(False, size, 0, 0, 0.0, 0.0, 0, size / max_bytes, selected_fps, ("size",))
        try:
            probe = await ffmpeg.probe(path, count_frames=True)
        except Exception:
            return QualityReport(False, size, 0, 0, 0.0, 0.0, 0, size / max_bytes, selected_fps, ("probe",))
        stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), None)
        if stream is None:
            return QualityReport(False, size, 0, 0, 0.0, 0.0, 0, size / max_bytes, selected_fps, ("no_video",))

        width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
        duration = float(probe.get("format", {}).get("duration") or stream.get("duration") or 0.0)
        rate = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1")
        try:
            num, den = rate.split("/", 1)
            fps = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)

        checks: list[str] = ["size"]
        dimensions_ok = (width, height) == (expected_width, expected_height)
        fps_ok = fps > 0 and abs(fps - selected_fps) <= 0.5
        duration_ok = expected_duration is None or (
            duration > 0 and abs(duration - expected_duration) <= duration_tolerance
        )
        frames_ok = frames >= min_frames
        if dimensions_ok:
            checks.append("dimensions")
        if fps_ok:
            checks.append("fps")
        if duration_ok:
            checks.append("duration")
        if frames_ok:
            checks.append("frames")

        valid = dimensions_ok and fps_ok and duration_ok and frames_ok
        return QualityReport(
            valid,
            size,
            width,
            height,
            duration,
            fps,
            frames,
            size / max_bytes,
            selected_fps,
            tuple(checks),
        )
