"""Deterministic explicit-time transitions for canonical RenderBuffer pairs."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer


@dataclass(frozen=True, slots=True)
class TemporalCrossfadeEffect:
    """Crossfade two RenderBuffer inputs over an explicit time interval."""

    start_time: float
    end_time: float

    def __post_init__(self) -> None:
        if not np.isfinite(float(self.start_time)) or not np.isfinite(float(self.end_time)):
            raise ValueError("temporal crossfade times must be finite")
        if self.end_time <= self.start_time:
            raise ValueError("temporal crossfade end_time must be greater than start_time")

    def __call__(
        self,
        inputs: tuple[RenderBuffer, ...],
        time: float,
    ) -> RenderBuffer:
        if len(inputs) != 2:
            raise ValueError("TemporalCrossfadeEffect requires exactly two RenderBuffer inputs")
        first, second = inputs
        if not isinstance(first, RenderBuffer) or not isinstance(second, RenderBuffer):
            raise TypeError("TemporalCrossfadeEffect inputs must be RenderBuffer values")
        if first.shape != second.shape:
            raise ValueError("TemporalCrossfadeEffect input shapes must match")
        if not np.isfinite(time):
            raise ValueError("temporal crossfade sample time must be finite")

        progress = float(
            np.clip(
                (float(time) - self.start_time) / (self.end_time - self.start_time),
                0.0,
                1.0,
            )
        )
        if progress == 0.0:
            return first.copy()
        if progress == 1.0:
            return second.copy()

        first_alpha = first.data[..., 3:4]
        second_alpha = second.data[..., 3:4]
        first_premultiplied = first.data[..., :3] * first_alpha
        second_premultiplied = second.data[..., :3] * second_alpha
        alpha = first_alpha + (second_alpha - first_alpha) * np.float32(progress)
        premultiplied = first_premultiplied + (
            second_premultiplied - first_premultiplied
        ) * np.float32(progress)
        rgb = np.divide(
            premultiplied,
            alpha,
            out=np.zeros_like(premultiplied),
            where=alpha > 0.0,
        )
        result = np.concatenate([rgb, alpha], axis=-1).astype(np.float32)
        return RenderBuffer.from_linear_rgba(result)
