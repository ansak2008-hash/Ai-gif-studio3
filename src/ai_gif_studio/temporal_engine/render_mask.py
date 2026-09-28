"""Canonical scalar mask values for selective rendering and effects."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class RenderMask:
    """Owned, read-only float32 coverage/control field."""

    _mask: np.ndarray

    def __post_init__(self) -> None:
        mask = np.asarray(self._mask)
        if mask.ndim != 2:
            raise ValueError("RenderMask data must have shape HxW")
        if mask.shape[0] < 1 or mask.shape[1] < 1:
            raise ValueError("RenderMask dimensions must be positive")
        if not np.issubdtype(mask.dtype, np.floating):
            raise TypeError("RenderMask data must be floating point")
        if not np.isfinite(mask).all():
            raise ValueError("RenderMask data must be finite")
        if np.any((mask < 0.0) | (mask > 1.0)):
            raise ValueError("RenderMask data must be within [0, 1]")

        owned = np.array(mask, dtype=np.float32, copy=True)
        owned.setflags(write=False)
        object.__setattr__(self, "_mask", owned)

    @classmethod
    def from_array(cls, value: np.ndarray) -> RenderMask:
        """Create a mask from validated floating-point HxW data."""
        return cls(value)

    @classmethod
    def allocate(
        cls,
        width: int,
        height: int,
        *,
        value: float = 0.0,
    ) -> RenderMask:
        """Allocate a constant canonical mask."""
        if width < 1 or height < 1:
            raise ValueError("RenderMask dimensions must be positive")
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("RenderMask value must be within [0, 1]")
        return cls(np.full((height, width), value, dtype=np.float32))

    @property
    def data(self) -> np.ndarray:
        """Return the read-only canonical mask data."""
        return self._mask

    @property
    def shape(self) -> tuple[int, int]:
        return self._mask.shape

    @property
    def dtype(self) -> np.dtype:
        return self._mask.dtype

    def copy(self) -> RenderMask:
        """Return an independent copy of this mask."""
        return RenderMask(self._mask.copy())
