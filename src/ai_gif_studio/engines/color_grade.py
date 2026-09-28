from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ColorGradeSpec:
    """Bounded deterministic RGB grading parameters."""

    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    temperature: float = 0.0
    tint: float = 0.0
    black_point: float = 0.0
    white_point: float = 1.0
    gamma: float = 1.0

    def __post_init__(self) -> None:
        if not -1.0 <= self.brightness <= 1.0:
            raise ValueError("brightness must be between -1 and 1")
        if not 0.0 <= self.contrast <= 4.0:
            raise ValueError("contrast must be between 0 and 4")
        if not 0.0 <= self.saturation <= 4.0:
            raise ValueError("saturation must be between 0 and 4")
        if not -1.0 <= self.temperature <= 1.0 or not -1.0 <= self.tint <= 1.0:
            raise ValueError("temperature and tint must be between -1 and 1")
        if not 0.0 <= self.black_point < self.white_point <= 1.0:
            raise ValueError("black_point must be below white_point in [0, 1]")
        if not 0.05 <= self.gamma <= 5.0:
            raise ValueError("gamma must be between 0.05 and 5")


def build_rgb_lut(spec: ColorGradeSpec) -> np.ndarray:
    """Build a 256-entry RGB LUT from the immutable grading specification."""
    x = np.linspace(0.0, 1.0, 256, dtype=np.float64)
    x = np.clip((x - spec.black_point) / (spec.white_point - spec.black_point), 0.0, 1.0)
    x = np.power(x, 1.0 / spec.gamma)
    x = np.clip((x - 0.5) * spec.contrast + 0.5 + spec.brightness, 0.0, 1.0)

    # Temperature shifts blue versus red; tint shifts green versus magenta.
    red = np.clip(x + spec.temperature * 0.12 + spec.tint * 0.04, 0.0, 1.0)
    green = np.clip(x - spec.tint * 0.08, 0.0, 1.0)
    blue = np.clip(x - spec.temperature * 0.12 + spec.tint * 0.04, 0.0, 1.0)
    return np.stack((red, green, blue), axis=1)


def apply_color_grade(frame: np.ndarray, spec: ColorGradeSpec) -> np.ndarray:
    """Apply deterministic RGB grading while preserving an optional alpha channel."""
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] not in (3, 4):
        raise ValueError("frame must have shape HxWx3 or HxWx4")
    if frame.dtype != np.uint8:
        raise ValueError("frame must use uint8 pixels")

    lut = build_rgb_lut(spec)
    rgb = frame[..., :3].astype(np.float64) / 255.0
    # Luma-preserving saturation around Rec.709 luminance.
    luma = (
        0.2126 * rgb[..., 0]
        + 0.7152 * rgb[..., 1]
        + 0.0722 * rgb[..., 2]
    )
    saturated = luma[..., None] + (rgb - luma[..., None]) * spec.saturation
    indices = np.clip(np.rint(saturated * 255.0), 0, 255).astype(np.uint8)
    graded = np.empty_like(indices)
    for channel in range(3):
        graded[..., channel] = lut[indices[..., channel], channel]
    if frame.shape[2] == 4:
        return np.dstack((graded, frame[..., 3]))
    return graded


def apply_color_grade_batch(frames: list[np.ndarray], spec: ColorGradeSpec) -> list[np.ndarray]:
    """Apply one immutable grading specification to a sequence of frames."""
    return [apply_color_grade(frame, spec) for frame in frames]
