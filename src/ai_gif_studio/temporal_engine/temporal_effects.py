"""Deterministic time-sampled effects for canonical RenderBuffer values."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer


@dataclass(frozen=True, slots=True)
class TemporalFadeEffect:
    """Apply a deterministic linear alpha ramp over an explicit time interval."""

    start_time: float
    end_time: float
    start_alpha: float = 1.0
    end_alpha: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.start_time,
            self.end_time,
            self.start_alpha,
            self.end_alpha,
        )
        if not all(np.isfinite(float(value)) for value in values):
            raise ValueError("temporal fade parameters must be finite")
        if self.end_time <= self.start_time:
            raise ValueError("temporal fade end_time must be greater than start_time")
        if not 0.0 <= self.start_alpha <= 1.0:
            raise ValueError("temporal fade start_alpha must be in [0, 1]")
        if not 0.0 <= self.end_alpha <= 1.0:
            raise ValueError("temporal fade end_alpha must be in [0, 1]")

    def __call__(
        self,
        inputs: tuple[RenderBuffer, ...],
        time: float,
    ) -> RenderBuffer:
        if len(inputs) != 1:
            raise ValueError("TemporalFadeEffect requires exactly one RenderBuffer input")
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("TemporalFadeEffect input must be a RenderBuffer")
        if not np.isfinite(time):
            raise ValueError("temporal fade sample time must be finite")

        progress = float(
            np.clip(
                (float(time) - self.start_time)
                / (self.end_time - self.start_time),
                0.0,
                1.0,
            )
        )
        alpha = self.start_alpha + (self.end_alpha - self.start_alpha) * progress
        result = np.array(source.data, dtype=np.float32, copy=True)
        result[..., 3] *= np.float32(alpha)
        return RenderBuffer.from_linear_rgba(result)
