"""Configuration for the crop-only conversion pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CropOnlyConfiguration:
    """Quality and output constraints for :func:`crop_video_to_gif`.

    ``fps_ladder`` is tried in its given order.  This intentionally keeps
    quality settings fixed while reducing frame rate only when necessary to
    meet the Telegram-friendly output-size limit.
    """

    output_size: int = 320
    default_duration_seconds: float = 6.0
    max_output_bytes: int = 2_400_000
    fps_ladder: tuple[int, ...] = (20, 16, 12, 10, 8, 6)
    palette_colors: int = 256

    def __post_init__(self) -> None:
        if self.output_size != 320:
            raise ValueError("Crop Only output_size must be exactly 320")
        if self.default_duration_seconds <= 0:
            raise ValueError("default_duration_seconds must be positive")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        if not self.fps_ladder or any(fps <= 0 for fps in self.fps_ladder):
            raise ValueError("fps_ladder must contain positive values")
        if tuple(sorted(self.fps_ladder, reverse=True)) != self.fps_ladder:
            raise ValueError("fps_ladder must be ordered from highest to lowest")
        if not 2 <= self.palette_colors <= 256:
            raise ValueError("palette_colors must be between 2 and 256")
