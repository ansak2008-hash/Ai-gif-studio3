from __future__ import annotations

import hashlib
from pathlib import Path

from ai_gif_studio.infrastructure.ffmpeg import FFmpegService

class OutputValidator:
    def __init__(self, ffmpeg: FFmpegService | None = None) -> None:
        self._ffmpeg = ffmpeg

    def validate_basic_gif(self, path: Path, max_bytes: int) -> bool:
        if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > max_bytes:
            return False
        try:
            return path.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
        except OSError:
            return False

    async def validate_gif(self, path: Path, max_bytes: int, width: int = 320, height: int = 320,
                           ffmpeg: FFmpegService | None = None, min_frames: int = 1,
                           max_frames: int | None = None, expected_fps: int | None = None,
                           expected_duration: float | None = None, duration_tolerance: float = 0.25) -> bool:
        if not self.validate_basic_gif(path, max_bytes):
            return False
        service = ffmpeg or self._ffmpeg
        if service is None:
            raise ValueError("FFmpegService is required for media validation")
        try:
            probe = await service.probe(path, count_frames=True)
        except Exception:
            return False
        stream = next((x for x in probe.get("streams", []) if x.get("codec_type") == "video"), None)
        if stream is None or int(stream.get("width", 0)) != width or int(stream.get("height", 0)) != height:
            return False
        frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
        if frames < min_frames or (max_frames is not None and frames > max_frames):
            return False
        if expected_fps is not None:
            try:
                n, d = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1").split("/", 1)
                actual_fps = float(n) / float(d)
            except (ValueError, ZeroDivisionError):
                return False
            if abs(actual_fps - expected_fps) > 0.5:
                return False
        if expected_duration is not None:
            try:
                actual_duration = float(probe.get("format", {}).get("duration") or stream.get("duration") or 0)
            except (TypeError, ValueError):
                return False
            if abs(actual_duration - expected_duration) > duration_tolerance:
                return False
        return True

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
