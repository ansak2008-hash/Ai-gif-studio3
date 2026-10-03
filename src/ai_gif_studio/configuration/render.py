from __future__ import annotations

from dataclasses import dataclass

RENDER_CONFIG_VERSION = 1
DEFAULT_FPS_LADDER = (30, 27, 24, 20, 18, 15)


@dataclass(frozen=True)
class RenderConfiguration:
    schema_version: int = RENDER_CONFIG_VERSION
    canvas_width: int = 320
    canvas_height: int = 320
    duration_seconds: float = 6.0
    maximum_output_bytes: int = 2_400_000
    preferred_fps: int = DEFAULT_FPS_LADDER[0]
    fps_fallback_ladder: tuple[int, ...] = DEFAULT_FPS_LADDER
    palette_colors: int = 256

    def __post_init__(self) -> None:
        if (self.canvas_width, self.canvas_height) != (320, 320):
            raise ValueError("MVP render canvas must be 320x320")
        if self.preferred_fps < 1 or self.preferred_fps > 30:
            raise ValueError("preferred FPS must be between 1 and 30")
        if not self.fps_fallback_ladder:
            raise ValueError("FPS fallback ladder must not be empty")
        if self.fps_fallback_ladder[0] != self.preferred_fps or any(
            a <= b for a, b in zip(self.fps_fallback_ladder, self.fps_fallback_ladder[1:])
        ):
            raise ValueError("FPS fallback ladder must descend from preferred FPS")
        if not 1 <= self.palette_colors <= 256:
            raise ValueError("palette_colors must be 1..256")
