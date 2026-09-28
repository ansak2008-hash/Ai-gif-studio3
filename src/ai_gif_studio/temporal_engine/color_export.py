"""Explicit linear-light color and GIF export boundary."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .color import encode_srgb


@dataclass(frozen=True)
class ExportColorSpec:
    background_linear: tuple[float, float, float] = (0.0, 0.0, 0.0)
    tone_mapping: str = "clamp"

    def __post_init__(self) -> None:
        if self.tone_mapping not in {"clamp", "reinhard"}:
            raise ValueError("tone_mapping must be 'clamp' or 'reinhard'")
        if len(self.background_linear) != 3 or not all(
            np.isfinite(float(v)) and float(v) >= 0.0 for v in self.background_linear
        ):
            raise ValueError("background_linear must contain three finite non-negative values")


def tone_map_reinhard(linear_rgb: np.ndarray) -> np.ndarray:
    """Compress non-negative HDR linear RGB into [0, 1] per channel."""
    rgb = np.maximum(np.asarray(linear_rgb, dtype=np.float64), 0.0)
    return rgb / (1.0 + rgb)


def linear_rgba_to_srgb_rgb(
    rgba_linear: np.ndarray,
    spec: ExportColorSpec | None = None,
) -> np.ndarray:
    """Composite linear RGBA over a linear background, then encode to sRGB uint8."""
    if spec is None:
        spec = ExportColorSpec()
    rgba = np.asarray(rgba_linear, dtype=np.float64)
    if rgba.ndim != 3 or rgba.shape[-1] != 4:
        raise ValueError("expected HxWx4 linear RGBA")
    if not np.isfinite(rgba).all():
        raise ValueError("linear RGBA must be finite")

    rgb = np.maximum(rgba[..., :3], 0.0)
    alpha = np.clip(rgba[..., 3], 0.0, 1.0)
    background = np.asarray(spec.background_linear, dtype=np.float64)
    composited = rgb * alpha[..., None] + background * (1.0 - alpha[..., None])

    if spec.tone_mapping == "reinhard":
        composited = tone_map_reinhard(composited)
    else:
        composited = np.clip(composited, 0.0, 1.0)
    return encode_srgb(composited)
