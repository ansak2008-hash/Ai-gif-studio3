"""Canonical linear RGBA render target contract for the temporal engine."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from weakref import WeakKeyDictionary

import numpy as np

from .color import linearize_srgb

_CONSTRUCTION_TOKEN = object()
_STORAGE_LOCK = RLock()
_STORAGE: WeakKeyDictionary[RenderBuffer, np.ndarray] = WeakKeyDictionary()


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True, init=False)
class RenderBuffer:
    """Owned float32 linear-light RGBA render storage.

    Canonical pixel storage is held outside the instance slots so even reflective
    replacement of instance attributes cannot swap the backing array. The public
    data view is read-only, and mutation happens only through explicit buffer
    operations.
    """

    _identity: object

    def __init__(self, storage: np.ndarray, *, _token: object | None = None) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise TypeError(
                "RenderBuffer must be created through from_linear_rgba(), "
                "from_srgb_u8(), or allocate()"
            )
        raw = np.asarray(storage)
        self._validate_shape(raw)
        if raw.dtype != np.float32:
            raise TypeError("RenderBuffer storage must use float32")
        self._validate_buffer_values(raw)
        owned = np.array(raw, dtype=np.float32, copy=True)
        owned.setflags(write=False)
        identity = object()
        object.__setattr__(self, "_identity", identity)
        with _STORAGE_LOCK:
            _STORAGE[self] = owned

    @classmethod
    def allocate(cls, width: int, height: int) -> RenderBuffer:
        """Allocate a transparent black linear RGBA buffer."""
        width_i = cls._positive_dimension(width, "width")
        height_i = cls._positive_dimension(height, "height")
        return cls(
            np.zeros((height_i, width_i, 4), dtype=np.float32),
            _token=_CONSTRUCTION_TOKEN,
        )

    @classmethod
    def from_linear_rgba(cls, rgba_linear: np.ndarray) -> RenderBuffer:
        """Create an owned buffer from floating-point linear RGBA."""
        raw = np.asarray(rgba_linear)
        if not np.issubdtype(raw.dtype, np.floating):
            raise TypeError("linear RGBA must use floating point values")
        return cls(np.asarray(raw, dtype=np.float32), _token=_CONSTRUCTION_TOKEN)

    @classmethod
    def from_srgb_u8(cls, rgba_srgb_u8: np.ndarray) -> RenderBuffer:
        """Create a canonical linear RGBA buffer from explicit sRGB uint8 input."""
        raw = np.asarray(rgba_srgb_u8)
        cls._validate_shape(raw)
        if raw.dtype != np.uint8:
            raise TypeError("sRGB RGBA input must use uint8")
        rgb_linear = linearize_srgb(raw[..., :3])
        alpha = raw[..., 3:4].astype(np.float32) / 255.0
        return cls(
            np.concatenate([rgb_linear, alpha], axis=-1).astype(np.float32),
            _token=_CONSTRUCTION_TOKEN,
        )

    @property
    def _rgba_linear(self) -> np.ndarray:
        """Backward-compatible read-only view of canonical linear storage."""
        return self.data

    @property
    def width(self) -> int:
        return int(self._storage_view().shape[1])

    @property
    def height(self) -> int:
        return int(self._storage_view().shape[0])

    @property
    def shape(self) -> tuple[int, int, int]:
        return self._storage_view().shape

    @property
    def dtype(self) -> np.dtype:
        return self._storage_view().dtype

    @property
    def data(self) -> np.ndarray:
        """Return a read-only view of the canonical RGBA storage."""
        view = self._storage_view().view()
        view.setflags(write=False)
        return view

    def clear(self, rgba_linear: tuple[float, float, float, float]) -> None:
        """Clear the buffer to one validated linear RGBA value."""
        value = np.asarray(rgba_linear, dtype=np.float32)
        if value.shape != (4,):
            raise ValueError("clear color must contain exactly four values")
        self._validate_color_value(value)
        current = self._storage_view()
        updated = np.broadcast_to(value, current.shape).copy()
        updated.setflags(write=False)
        with _STORAGE_LOCK:
            _STORAGE[self] = updated

    def copy(self) -> RenderBuffer:
        """Return an independent owned copy."""
        return RenderBuffer(self._storage_view(), _token=_CONSTRUCTION_TOKEN)

    def _storage_view(self) -> np.ndarray:
        with _STORAGE_LOCK:
            storage = _STORAGE.get(self)
        if storage is None:
            raise RuntimeError("RenderBuffer storage is unavailable")
        return storage

    @staticmethod
    def _positive_dimension(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{name} must be an integer")
        value_i = int(value)
        if value_i < 1:
            raise ValueError(f"{name} must be positive")
        return value_i

    @staticmethod
    def _validate_shape(raw: np.ndarray) -> None:
        if raw.ndim != 3 or raw.shape[2] != 4:
            raise ValueError("RenderBuffer must be HxWx4 RGBA")
        if raw.shape[0] < 1 or raw.shape[1] < 1:
            raise ValueError("RenderBuffer dimensions must be positive")

    @staticmethod
    def _validate_buffer_values(values: np.ndarray) -> None:
        if not np.isfinite(values).all():
            raise ValueError("RenderBuffer values must be finite")
        if np.any(values[..., :3] < 0.0):
            raise ValueError(
                "RenderBuffer RGB must contain non-negative linear-light values"
            )
        if np.any((values[..., 3] < 0.0) | (values[..., 3] > 1.0)):
            raise ValueError("RenderBuffer alpha must be in [0, 1]")

    @staticmethod
    def _validate_color_value(values: np.ndarray) -> None:
        if not np.isfinite(values).all():
            raise ValueError("RenderBuffer values must be finite")
        if np.any(values[:3] < 0.0):
            raise ValueError(
                "RenderBuffer RGB must contain non-negative linear-light values"
            )
        if values[3] < 0.0 or values[3] > 1.0:
            raise ValueError("RenderBuffer alpha must be in [0, 1]")
