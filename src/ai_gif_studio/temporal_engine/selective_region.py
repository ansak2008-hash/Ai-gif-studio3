"""Deterministic selective-region application for unary RenderBuffer transforms."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer
from .render_mask import RenderMask

RegionTransform = Callable[[tuple[RenderBuffer, ...]], RenderBuffer]


@dataclass(frozen=True, slots=True)
class SelectiveRegionEffect:
    """Apply a unary RenderBuffer transform only where a canonical mask covers."""

    transform: RegionTransform
    mask: RenderMask

    def __post_init__(self) -> None:
        if not callable(self.transform):
            raise TypeError("transform must be callable")
        if not isinstance(self.mask, RenderMask):
            raise TypeError("mask must be a RenderMask")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        if len(inputs) != 1:
            raise ValueError(
                "SelectiveRegionEffect requires exactly one RenderBuffer input"
            )
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("SelectiveRegionEffect input must be a RenderBuffer")
        if self.mask.shape != source.shape[:2]:
            raise ValueError(
                "render mask dimensions must match RenderBuffer dimensions"
            )

        transformed_input = source.copy()
        processed = self.transform((transformed_input,))
        if not isinstance(processed, RenderBuffer):
            raise TypeError("selective transform must return a RenderBuffer")
        if processed is transformed_input:
            raise ValueError(
                "selective transform must return a new RenderBuffer"
            )
        if processed.shape != source.shape:
            raise ValueError("selective transform changed render dimensions")

        mask = self.mask.data
        if np.all(mask == 0.0):
            return source.copy()
        if np.all(mask == 1.0):
            return processed.copy()

        coverage = mask[..., None]
        blended = (
            source.data * (1.0 - coverage) + processed.data * coverage
        ).astype(np.float32, copy=False)
        return RenderBuffer.from_linear_rgba(blended)
