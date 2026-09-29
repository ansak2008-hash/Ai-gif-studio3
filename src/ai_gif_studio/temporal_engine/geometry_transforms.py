"""Deterministic affine and perspective transforms for canonical RenderBuffer values."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .render_buffer import RenderBuffer


@dataclass(frozen=True, slots=True)
class AffineTransformSpec:
    """Validated affine transform and target geometry."""

    width: int
    height: int
    matrix: np.ndarray

    def __post_init__(self) -> None:
        self._validate_dimensions()
        matrix = np.asarray(self.matrix)
        if matrix.shape != (2, 3):
            raise ValueError("affine matrix must have shape 2x3")
        if not np.issubdtype(matrix.dtype, np.number):
            raise TypeError("affine matrix must contain numeric values")
        if not np.isfinite(matrix).all():
            raise ValueError("affine matrix must contain finite values")
        if np.linalg.matrix_rank(matrix[:, :2]) < 2:
            raise ValueError("affine transform must have a non-degenerate linear component")
        owned = np.array(matrix, dtype=np.float64, copy=True)
        owned.setflags(write=False)
        object.__setattr__(self, "matrix", owned)

    def _validate_dimensions(self) -> None:
        if isinstance(self.width, bool) or not isinstance(self.width, (int, np.integer)):
            raise TypeError("affine width must be an integer")
        if isinstance(self.height, bool) or not isinstance(self.height, (int, np.integer)):
            raise TypeError("affine height must be an integer")
        if int(self.width) < 1 or int(self.height) < 1:
            raise ValueError("affine dimensions must be positive")


@dataclass(frozen=True, slots=True)
class PerspectiveTransformSpec:
    """Validated four-point projective transform and target geometry."""

    width: int
    height: int
    source_points: np.ndarray
    destination_points: np.ndarray

    def __post_init__(self) -> None:
        self._validate_dimensions()
        source = self._validate_points(self.source_points, "source")
        destination = self._validate_points(self.destination_points, "destination")
        matrix = cv2.getPerspectiveTransform(
            source.astype(np.float32),
            destination.astype(np.float32),
        )
        if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < 3:
            raise ValueError("perspective points must define a non-degenerate transform")
        object.__setattr__(self, "source_points", source)
        object.__setattr__(self, "destination_points", destination)

    def _validate_dimensions(self) -> None:
        if isinstance(self.width, bool) or not isinstance(self.width, (int, np.integer)):
            raise TypeError("perspective width must be an integer")
        if isinstance(self.height, bool) or not isinstance(self.height, (int, np.integer)):
            raise TypeError("perspective height must be an integer")
        if int(self.width) < 1 or int(self.height) < 1:
            raise ValueError("perspective dimensions must be positive")

    @staticmethod
    def _validate_points(points: np.ndarray, name: str) -> np.ndarray:
        raw = np.asarray(points)
        if raw.shape != (4, 2):
            raise ValueError(f"{name} points must have shape 4x2")
        if not np.issubdtype(raw.dtype, np.number):
            raise TypeError(f"{name} points must contain numeric values")
        if not np.isfinite(raw).all():
            raise ValueError(f"{name} points must contain finite values")
        owned = np.array(raw, dtype=np.float64, copy=True)
        owned.setflags(write=False)
        return owned


@dataclass(frozen=True, slots=True)
class AffineTransformEffect:
    """Apply one deterministic affine transform to a RenderBuffer."""

    spec: AffineTransformSpec

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "AffineTransformEffect")
        transformed = cv2.warpAffine(
            source.data,
            self.spec.matrix,
            (int(self.spec.width), int(self.spec.height)),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0,
        )
        return RenderBuffer.from_linear_rgba(transformed)


@dataclass(frozen=True, slots=True)
class PerspectiveTransformEffect:
    """Apply one deterministic four-point perspective transform to a RenderBuffer."""

    spec: PerspectiveTransformSpec

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs, "PerspectiveTransformEffect")
        matrix = cv2.getPerspectiveTransform(
            self.spec.source_points.astype(np.float32),
            self.spec.destination_points.astype(np.float32),
        )
        transformed = cv2.warpPerspective(
            source.data,
            matrix,
            (int(self.spec.width), int(self.spec.height)),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0,
        )
        return RenderBuffer.from_linear_rgba(transformed)


def _single_input(inputs: tuple[RenderBuffer, ...], effect_name: str) -> RenderBuffer:
    if len(inputs) != 1:
        raise ValueError(f"{effect_name} requires exactly one RenderBuffer input")
    source = inputs[0]
    if not isinstance(source, RenderBuffer):
        raise TypeError(f"{effect_name} input must be a RenderBuffer")
    return source
