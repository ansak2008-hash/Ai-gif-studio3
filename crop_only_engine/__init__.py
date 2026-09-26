"""A standalone, crop-only video-to-GIF engine."""

from .config import CropOnlyConfiguration
from .engine import CropOnlyResult, CropOnlyError, crop_video_to_gif

__all__ = [
    "CropOnlyConfiguration",
    "CropOnlyError",
    "CropOnlyResult",
    "crop_video_to_gif",
]
