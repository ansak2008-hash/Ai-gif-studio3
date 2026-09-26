from __future__ import annotations

import hashlib
from pathlib import Path

from ai_gif_studio.infrastructure.ffmpeg import FFmpegService


class OutputValidator:
    def __init__(self, ffmpeg: FFmpegService | None = None) -> None:
        self._ffmpeg = ffmpeg

    def validate_basic_gif(self, path: Path, max_bytes: int) -> bool:
        if not path.is_file():
            return False
        if path.stat().st_size <= 0 or path.stat().st_size > max_bytes:
            return False
        try:
            return path.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
        except OSError:
            return False

    async def validate_gif(
        self,
        path: Path,
        max_bytes: int,
        width: int = 320,
        height: int = 320,
        ffmpeg: FFmpegService | None = None,
    ) -> bool:
        if not self.validate_basic_gif(path, max_bytes):
            return False
        service = ffmpeg or self._ffmpeg
        if service is None:
            raise ValueError("FFmpegService is required for media validation")
        try:
            probe = await service.probe(path)
        except Exception:
            return False
        stream = next(
            (item for item in probe.get("streams", []) if item.get("codec_type") == "video"),
            None,
        )
        if stream is None:
            return False
        return int(stream.get("width", 0)) == width and int(stream.get("height", 0)) == height

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
