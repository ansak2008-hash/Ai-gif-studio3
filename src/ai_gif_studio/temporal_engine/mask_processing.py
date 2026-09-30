"""Deterministic raster processing for persistent mask state."""
from __future__ import annotations

import math

import numpy as np

from ai_gif_studio.domain.mask_state import MaskState
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask


def _box_blur(values: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0.0:
        return values
    height, width = values.shape
    limit = max(height, width) - 1
    effective = min(math.ceil(radius), limit)
    if effective <= 0:
        return values

    def blur_axis(data: np.ndarray, axis: int) -> np.ndarray:
        pad_width = [(0, 0), (0, 0)]
        pad_width[axis] = (effective, effective)
        padded = np.pad(data, pad_width, mode="edge")
        cumulative = np.cumsum(padded, axis=axis, dtype=np.float64)
        zeros_shape = list(cumulative.shape)
        zeros_shape[axis] = 1
        cumulative = np.concatenate(
            (np.zeros(zeros_shape, dtype=np.float64), cumulative),
            axis=axis,
        )
        length = 2 * effective + 1
        slices_end = [slice(None), slice(None)]
        slices_start = [slice(None), slice(None)]
        slices_end[axis] = slice(length, None)
        slices_start[axis] = slice(None, -length)
        return (cumulative[tuple(slices_end)] - cumulative[tuple(slices_start)]) / length

    return blur_axis(blur_axis(values, axis=1), axis=0)


def process_mask(source: RenderMask, state: MaskState) -> RenderMask:
    """Apply persistent mask semantics in their contractual order.

    Spatial processing uses a deterministic edge-padded box filter. A requested
    radius larger than the source extent is clamped to the largest meaningful
    pixel radius, preventing unbounded kernel/storage growth.
    """
    if not isinstance(source, RenderMask):
        raise TypeError("source must be a RenderMask")
    if not isinstance(state, MaskState):
        raise TypeError("state must be a MaskState")
    if not state.enabled:
        return RenderMask.allocate(source.shape[1], source.shape[0], value=1.0)

    values = np.asarray(source.data, dtype=np.float64).copy()
    values = _box_blur(values, state.feather_radius)
    values = _box_blur(values, state.blur_radius)

    values = np.clip(
        (values - state.levels_low) / (state.levels_high - state.levels_low),
        0.0,
        1.0,
    )
    if state.threshold is not None:
        values = np.where(values < state.threshold, 0.0, 1.0)
    if state.inverted:
        values = 1.0 - values
    values *= state.opacity
    return RenderMask.from_array(values.astype(np.float32))


def mask_from_alpha(source: RenderBuffer) -> RenderMask:
    """Create a canonical mask from the source buffer's linear alpha."""
    if not isinstance(source, RenderBuffer):
        raise TypeError("source must be a RenderBuffer")
    return RenderMask.from_array(source.data[..., 3])


def mask_from_luminance(source: RenderBuffer) -> RenderMask:
    """Create a canonical mask from clamped linear Rec.709 luminance.

    RGB values are interpreted as linear-light values. Alpha is deliberately
    ignored. HDR luminance above one is clamped to one at this mask boundary.
    """
    if not isinstance(source, RenderBuffer):
        raise TypeError("source must be a RenderBuffer")
    rgb = np.asarray(source.data[..., :3], dtype=np.float64)
    luminance = np.clip(
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2],
        0.0,
        1.0,
    )
    return RenderMask.from_array(luminance.astype(np.float32))
