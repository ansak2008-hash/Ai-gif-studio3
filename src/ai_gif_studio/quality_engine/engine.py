from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


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
    def ladder(self, preferred: int, current_size: int | None = None, max_bytes: int = 2_400_000) -> tuple[int, ...]:
        candidates = tuple(dict.fromkeys((preferred, 20, 16, 12, 10, 8, 6)))
        return tuple(fps for fps in candidates if fps > 0)

    async def inspect(
        self, path: Path, ffmpeg, max_bytes: int,
        expected_width: int = 320, expected_height: int = 320, selected_fps: int = 20,
    ) -> QualityReport:
        if not path.is_file():
            return QualityReport(False, 0, 0, 0, 0.0, 0.0, 0, 1.0, selected_fps, ("missing",))
        size = path.stat().st_size
        probe = await ffmpeg.probe(path)
        stream = next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), None)
        if stream is None:
            return QualityReport(False, size, 0, 0, 0.0, 0.0, 0, size / max_bytes, selected_fps, ("no_video",))
        width, height = int(stream.get("width") or 0), int(stream.get("height") or 0)
        duration = float(probe.get("format", {}).get("duration") or 0.0)
        rate = str(stream.get("r_frame_rate") or "0/1")
        try:
            num, den = rate.split("/", 1)
            fps = float(num) / max(float(den), 1.0)
        except ValueError:
            fps = 0.0
        frames = int(stream.get("nb_frames") or 0)
        checks = []
        if size <= max_bytes:
            checks.append("size")
        if (width, height) == (expected_width, expected_height):
            checks.append("dimensions")
        if duration > 0:
            checks.append("duration")
        valid = size > 0 and size <= max_bytes and (width, height) == (expected_width, expected_height)
        return QualityReport(valid, size, width, height, duration, fps, frames, size / max_bytes, selected_fps, tuple(checks))
