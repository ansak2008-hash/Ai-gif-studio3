"""Deterministic crop, fit, and fill transforms for canonical RenderBuffer values."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np

from .render_buffer import RenderBuffer


class FramingMode(StrEnum):
    """Geometry policy for fitting a source into a target rectangle."""

    CROP = "crop"
    FIT = "fit"
    FILL = "fill"


@dataclass(frozen=True, slots=True)
class FramingSpec:
    """Validated target geometry and normalized crop focus."""

    width: int
    height: int
    mode: FramingMode = FramingMode.FILL
    focus_x: float = 0.5
    focus_y: float = 0.5

    def __post_init__(self) -> None:
        if isinstance(self.width, bool) or not isinstance(self.width, (int, np.integer)):
            raise TypeError("framing width must be an integer")
        if isinstance(self.height, bool) or not isinstance(self.height, (int, np.integer)):
            raise TypeError("framing height must be an integer")
        if int(self.width) < 1 or int(self.height) < 1:
            raise ValueError("framing dimensions must be positive")
        if not isinstance(self.mode, FramingMode):
            raise TypeError("framing mode must be a FramingMode")
        if not np.isfinite(self.focus_x) or not np.isfinite(self.focus_y):
            raise ValueError("framing focus must be finite")
        if not 0.0 <= self.focus_x <= 1.0 or not 0.0 <= self.focus_y <= 1.0:
            raise ValueError("framing focus must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class FramingEffect:
    """Apply one deterministic framing policy to a canonical RenderBuffer."""

    spec: FramingSpec

    def __post_init__(self) -> None:
        if not isinstance(self.spec, FramingSpec):
            raise TypeError("spec must be a FramingSpec")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        if len(inputs) != 1:
            raise ValueError("FramingEffect requires exactly one RenderBuffer input")
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("FramingEffect input must be a RenderBuffer")

        if self.spec.mode is FramingMode.CROP:
            return _crop(source, self.spec)
        if self.spec.mode is FramingMode.FIT:
            return _fit(source, self.spec)
        if self.spec.mode is FramingMode.FILL:
            return _fill(source, self.spec)
        raise ValueError(f"unsupported framing mode: {self.spec.mode}")


def _crop(source: RenderBuffer, spec: FramingSpec) -> RenderBuffer:
    if spec.width > source.width or spec.height > source.height:
        raise ValueError("crop target dimensions cannot exceed source dimensions")

    x = _focus_offset(source.width - spec.width, spec.focus_x)
    y = _focus_offset(source.height - spec.height, spec.focus_y)
    cropped = source.data[y : y + spec.height, x : x + spec.width]
    return RenderBuffer.from_linear_rgba(cropped)


def _fit(source: RenderBuffer, spec: FramingSpec) -> RenderBuffer:
    scale = min(spec.width / source.width, spec.height / source.height)
    resized = _resize(source, scale)
    output = np.zeros(
        (spec.height, spec.width, 4),
        dtype=np.float32,
    )
    x = (spec.width - resized.width) // 2
    y = (spec.height - resized.height) // 2
    output[y : y + resized.height, x : x + resized.width] = resized.data
    return RenderBuffer.from_linear_rgba(output)


def _fill(source: RenderBuffer, spec: FramingSpec) -> RenderBuffer:
    scale = max(spec.width / source.width, spec.height / source.height)
    resized = _resize(source, scale)
    x = _focus_offset(resized.width - spec.width, spec.focus_x)
    y = _focus_offset(resized.height - spec.height, spec.focus_y)
    cropped = resized.data[y : y + spec.height, x : x + spec.width]
    return RenderBuffer.from_linear_rgba(cropped)


def _resize(source: RenderBuffer, scale: float) -> RenderBuffer:
    width = max(1, round(source.width * scale))
    height = max(1, round(source.height * scale))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(source.data, (width, height), interpolation=interpolation)
    return RenderBuffer.from_linear_rgba(resized)


def _focus_offset(available: int, focus: float) -> int:
    return min(available, max(0, round(available * focus)))
