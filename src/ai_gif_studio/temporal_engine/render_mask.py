"""Canonical scalar mask values for selective rendering and effects."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from weakref import WeakKeyDictionary

import numpy as np

_MASK_STORAGE_LOCK = RLock()
_MASK_STORAGE: WeakKeyDictionary[
    RenderMask, tuple[bytes, tuple[int, int], np.ndarray]
] = WeakKeyDictionary()


def _build_mask_storage(
    owned: np.ndarray,
) -> tuple[bytes, tuple[int, int], np.ndarray]:
    raw_bytes = owned.tobytes()
    shape = tuple(int(value) for value in owned.shape)
    view = np.ndarray(shape, dtype=np.float32, buffer=raw_bytes)
    if view.flags.writeable:
        raise RuntimeError("immutable RenderMask storage unexpectedly writable")
    return raw_bytes, shape, view


@dataclass(frozen=True, slots=True, weakref_slot=True, init=False)
class RenderMask:
    """Owned, read-only float32 coverage/control field."""

    def __init__(self, mask: np.ndarray) -> None:
        raw = np.asarray(mask)
        if raw.ndim != 2:
            raise ValueError("RenderMask data must have shape HxW")
        if raw.shape[0] < 1 or raw.shape[1] < 1:
            raise ValueError("RenderMask dimensions must be positive")
        if not np.issubdtype(raw.dtype, np.floating):
            raise TypeError("RenderMask data must be floating point")
        if not np.isfinite(raw).all():
            raise ValueError("RenderMask data must be finite")
        if np.any((raw < 0.0) | (raw > 1.0)):
            raise ValueError("RenderMask data must be within [0, 1]")
        owned = np.array(raw, dtype=np.float32, copy=True, order="C")
        with _MASK_STORAGE_LOCK:
            _MASK_STORAGE[self] = _build_mask_storage(owned)

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
        if isinstance(width, bool) or isinstance(height, bool):
            raise TypeError("RenderMask dimensions must be integers")
        if not isinstance(width, (int, np.integer)) or not isinstance(
            height, (int, np.integer)
        ):
            raise TypeError("RenderMask dimensions must be integers")
        if width < 1 or height < 1:
            raise ValueError("RenderMask dimensions must be positive")
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("RenderMask value must be within [0, 1]")
        return cls(np.full((height, width), value, dtype=np.float32))

    @property
    def data(self) -> np.ndarray:
        """Return the cached read-only canonical mask data."""
        with _MASK_STORAGE_LOCK:
            storage = _MASK_STORAGE.get(self)
        if storage is None:
            raise RuntimeError("RenderMask storage is unavailable")
        return storage[2]

    @property
    def shape(self) -> tuple[int, int]:
        with _MASK_STORAGE_LOCK:
            storage = _MASK_STORAGE.get(self)
        if storage is None:
            raise RuntimeError("RenderMask storage is unavailable")
        return storage[1]

    @property
    def dtype(self) -> np.dtype:
        return np.dtype(np.float32)

    def copy(self) -> RenderMask:
        """Return an independent copy of this mask."""
        return RenderMask(self.data)
