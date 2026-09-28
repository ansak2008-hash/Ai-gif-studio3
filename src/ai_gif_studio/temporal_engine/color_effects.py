"""Reusable unary color effects over canonical RenderBuffer values."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer


def _single_input(
    inputs: tuple[RenderBuffer, ...], effect_name: str
) -> RenderBuffer:
    if len(inputs) != 1:
        raise ValueError(f"{effect_name} requires exactly one RenderBuffer input")
    source = inputs[0]
    if not isinstance(source, RenderBuffer):
        raise TypeError(f"{effect_name} input must be a RenderBuffer")
    return source


@dataclass(frozen=True, slots=True)
class ExposureEffect:
    """Deterministic linear-RGB exposure adjustment."""

    exposure_stops: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.exposure_stops):
            raise ValueError("exposure_stops must be finite")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "ExposureEffect")

        scale = 2.0 ** self.exposure_stops
        data = source.data.copy()
        data[..., :3] *= scale
        return RenderBuffer.from_linear_rgba(data)


@dataclass(frozen=True, slots=True)
class GammaEffect:
    """Deterministic power-law transform in canonical linear RGB."""

    gamma: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.gamma) or self.gamma <= 0.0:
            raise ValueError("gamma must be finite and greater than zero")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "GammaEffect")

        data = source.data.copy()
        data[..., :3] = np.power(data[..., :3], self.gamma)
        return RenderBuffer.from_linear_rgba(data)


@dataclass(frozen=True, slots=True)
class RGBGainEffect:
    """Deterministic per-channel gain in canonical linear RGB."""

    red: float
    green: float
    blue: float

    def __post_init__(self) -> None:
        gains = (self.red, self.green, self.blue)
        if not all(np.isfinite(gain) and gain >= 0.0 for gain in gains):
            raise ValueError("RGB gains must be finite and nonnegative")

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "RGBGainEffect")

        data = source.data.copy()
        data[..., 0] *= self.red
        data[..., 1] *= self.green
        data[..., 2] *= self.blue
        return RenderBuffer.from_linear_rgba(data)


@dataclass(frozen=True, slots=True)
class ColorMatrixEffect:
    """Deterministic affine transform over canonical linear RGB."""

    _matrix: np.ndarray

    def __post_init__(self) -> None:
        matrix = np.asarray(self._matrix)
        if matrix.shape != (3, 4):
            raise ValueError("color matrix must have shape (3, 4)")
        if not np.issubdtype(matrix.dtype, np.floating):
            raise TypeError("color matrix must be floating point")
        if not np.isfinite(matrix).all():
            raise ValueError("color matrix must be finite")

        owned = np.array(matrix, dtype=np.float32, copy=True)
        if not np.isfinite(owned).all():
            raise ValueError("color matrix must remain finite in float32 storage")
        owned.setflags(write=False)
        object.__setattr__(self, "_matrix", owned)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> ColorMatrixEffect:
        """Construct a color matrix effect from a 3x4 affine matrix."""
        return cls(matrix)

    @property
    def matrix(self) -> np.ndarray:
        """Return the immutable owned affine matrix."""
        return self._matrix

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "ColorMatrixEffect")

        rgb = source.data[..., :3]
        transformed = np.matmul(rgb, self._matrix[:, :3].T) + self._matrix[:, 3]
        data = source.data.copy()
        data[..., :3] = transformed
        return RenderBuffer.from_linear_rgba(data)
