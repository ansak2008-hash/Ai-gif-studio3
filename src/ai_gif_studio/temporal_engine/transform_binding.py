"""Explicit adapter from immutable project transform state to RenderBuffer."""
from __future__ import annotations

import numpy as np

from ai_gif_studio.domain.transforms import MAX_COORDINATE, TransformState

from .geometry_transforms import AffineTransformEffect, AffineTransformSpec
from .render_buffer import RenderBuffer


def apply_transform_state(source: RenderBuffer, state: TransformState) -> RenderBuffer:
    """Apply a validated project transform to a canonical 320x320 RenderBuffer."""
    if not isinstance(source, RenderBuffer):
        raise TypeError("source must be a RenderBuffer")
    if not isinstance(state, TransformState):
        raise TypeError("state must be a TransformState")
    if source.width != int(MAX_COORDINATE) or source.height != int(MAX_COORDINATE):
        raise ValueError("transform binding requires a 320x320 RenderBuffer")

    x, y, width, height = state.crop
    cropped = source.data[y : y + height, x : x + width]
    cropped_buffer = RenderBuffer.from_linear_rgba(cropped)

    if state.scale == 1.0 and state.x == 0.0 and state.y == 0.0:
        return cropped_buffer.copy()

    center_x = width / 2.0
    center_y = height / 2.0
    matrix = np.array(
        [
            [state.scale, 0.0, (1.0 - state.scale) * center_x + state.x],
            [0.0, state.scale, (1.0 - state.scale) * center_y + state.y],
        ],
        dtype=np.float64,
    )
    effect = AffineTransformEffect(
        AffineTransformSpec(width, height, matrix)
    )
    return effect((cropped_buffer,))
