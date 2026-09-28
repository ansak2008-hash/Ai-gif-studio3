"""Deterministic binary blend modes with optional canonical masks."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from .render_buffer import RenderBuffer
from .render_mask import RenderMask

class BlendMode(str, Enum):
    """Supported unassociated-RGB blend formulas."""

    NORMAL = 'normal'
    MULTIPLY = 'multiply'
    SCREEN = 'screen'
    OVERLAY = 'overlay'

@dataclass(frozen=True, slots=True)
class BlendModeEffect:
    """Composite a source layer over a destination using a typed blend mode."""

    mode: BlendMode = BlendMode.NORMAL
    mask: RenderMask | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, BlendMode):
            raise TypeError('mode must be a BlendMode')
        if self.mask is not None and not isinstance(self.mask, RenderMask):
            raise TypeError('mask must be a RenderMask')

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        if len(inputs) != 2:
            raise ValueError('BlendModeEffect requires exactly two RenderBuffer inputs')
        destination, source = inputs
        if not isinstance(destination, RenderBuffer) or not isinstance(source, RenderBuffer):
            raise TypeError('BlendModeEffect inputs must be RenderBuffer values')
        if destination.shape != source.shape:
            raise ValueError('source and destination RenderBuffer shapes must match')
        if self.mask is not None and self.mask.shape != destination.shape:
            raise ValueError('mask shape must match RenderBuffer shape')

        dst = np.asarray(destination.data, dtype=np.float64)
        src = np.asarray(source.data, dtype=np.float64)
        dst_rgb = dst[..., :3]
        src_rgb = src[..., :3]
        dst_alpha = dst[..., 3:4]
        src_alpha = src[..., 3:4]
        if self.mask is not None:
            src_alpha = src_alpha * np.asarray(self.mask.data, dtype=np.float64)[..., None]

        blended = _blend_rgb(self.mode, dst_rgb, src_rgb)
        inverse_src_alpha = 1.0 - src_alpha
        alpha = src_alpha + dst_alpha * inverse_src_alpha
        premultiplied = blended * src_alpha + dst_rgb * dst_alpha * inverse_src_alpha
        rgb = np.divide(premultiplied, alpha, out=np.zeros_like(premultiplied), where=alpha > 0.0)
        result = np.concatenate([rgb, alpha], axis=-1).astype(np.float32)
        return RenderBuffer.from_linear_rgba(result)

def _blend_rgb(mode: BlendMode, destination: np.ndarray, source: np.ndarray) -> np.ndarray:
    if mode is BlendMode.NORMAL:
        return source
    if mode is BlendMode.MULTIPLY:
        return destination * source
    if mode is BlendMode.SCREEN:
        return 1.0 - (1.0 - destination) * (1.0 - source)
    if mode is BlendMode.OVERLAY:
        return np.where(destination <= 0.5, 2.0 * destination * source, 1.0 - 2.0 * (1.0 - destination) * (1.0 - source))
    raise AssertionError(f'unsupported blend mode: {mode!r}')
