"""Reusable unary color effects over canonical RenderBuffer values."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer


@dataclass(frozen=True, slots=True)
class ExposureEffect:
    """Deterministic linear-RGB exposure adjustment."""

    exposure_stops: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.exposure_stops):
            raise ValueError("exposure_stops must be finite")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        if len(inputs) != 1:
            raise ValueError("ExposureEffect requires exactly one RenderBuffer input")
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("ExposureEffect input must be a RenderBuffer")

        scale = 2.0 ** self.exposure_stops
        data = source.data.copy()
        data[..., :3] *= scale
        return RenderBuffer.from_linear_rgba(data)
