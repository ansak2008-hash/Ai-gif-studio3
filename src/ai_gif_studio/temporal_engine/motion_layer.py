"""Deterministic per-layer affine motion over canonical RenderBuffer layers."""
from __future__ import annotations

from dataclasses import dataclass

from .blend import BlendMode
from .compositor import BlendLayer
from .geometry_transforms import AffineTransformEffect
from .keyframed_transforms import AffineTransformTrack
from .render_buffer import RenderBuffer
from .render_mask import RenderMask


@dataclass(frozen=True, slots=True)
class MotionLayer:
    """Immutable layer descriptor with time-sampled affine motion."""

    source: RenderBuffer
    track: AffineTransformTrack
    mode: BlendMode = BlendMode.NORMAL
    mask: RenderMask | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, RenderBuffer):
            raise TypeError("source must be a RenderBuffer")
        if not isinstance(self.track, AffineTransformTrack):
            raise TypeError("track must be an AffineTransformTrack")
        if self.source.shape != (int(self.track.height), int(self.track.width), 4):
            raise ValueError("source dimensions must match motion track target dimensions")
        if not isinstance(self.mode, BlendMode):
            raise TypeError("mode must be a BlendMode")
        if self.mask is not None:
            if not isinstance(self.mask, RenderMask):
                raise TypeError("mask must be a RenderMask")
            if self.mask.shape != self.source.shape[:2]:
                raise ValueError("mask dimensions must match source dimensions")

    def sample(self, time: float) -> BlendLayer:
        """Sample the layer motion and return a canonical compositing layer."""
        transformed = AffineTransformEffect(self.track.sample(time))((self.source,))
        return BlendLayer(source=transformed, mode=self.mode, mask=self.mask)
