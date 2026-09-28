"""Deterministic explicit-time orchestration for moving RenderBuffer layers."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from .compositor import composite_blend_layers
from .motion_layer import MotionLayer
from .render_buffer import RenderBuffer


def composite_motion_layers(
    base: RenderBuffer,
    layers: Iterable[MotionLayer],
    time: float,
) -> RenderBuffer:
    """Sample ordered motion layers at time and composite them over base."""
    if not isinstance(base, RenderBuffer):
        raise TypeError("base must be a RenderBuffer")
    if not np.isfinite(time):
        raise ValueError("motion layer sample time must be finite")

    sampled = []
    for layer in layers:
        if not isinstance(layer, MotionLayer):
            raise TypeError("layers must contain MotionLayer values")
        sampled.append(layer.sample(float(time)))
    return composite_blend_layers(base, sampled)
