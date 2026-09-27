from __future__ import annotations

from dataclasses import dataclass


RENDER_CONFIG_VERSION = 1


@dataclass(frozen=True)
class RenderConfiguration:
    schema_version: int = RENDER_CONFIG_VERSION
    canvas_width: int = 320
    canvas_height: int = 320
    duration_seconds: float = 6.0
    maximum_output_bytes: int = 2_400_000
    preferred_fps: int = 20
    fps_fallback_ladder: tuple[int, ...] = (20, 16, 12, 10, 8, 6)
    palette_colors: int = 256

    def __post_init__(self) -> None:
        if (self.canvas_width, self.canvas_height) != (320, 320):
            raise ValueError("MVP render canvas must be 320x320")
        if self.fps_fallback_ladder[0] != self.preferred_fps or any(
            a <= b for a, b in zip(self.fps_fallback_ladder, self.fps_fallback_ladder[1:])
        ):
            raise ValueError("FPS fallback ladder must descend from preferred FPS")
        if not 1 <= self.palette_colors <= 256:
            raise ValueError("palette_colors must be 1..256")
