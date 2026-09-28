"""Deterministic keyframed affine transform parameter sampling."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry_transforms import AffineTransformSpec


@dataclass(frozen=True, slots=True)
class AffineTransformKeyframe:
    """One validated affine transform parameter sample."""

    time: float
    matrix: np.ndarray

    def __post_init__(self) -> None:
        if not np.isfinite(self.time):
            raise ValueError("keyframe time must be finite")
        matrix = np.asarray(self.matrix)
        if matrix.shape != (2, 3):
            raise ValueError("keyframe affine matrix must have shape 2x3")
        if not np.issubdtype(matrix.dtype, np.number):
            raise TypeError("keyframe affine matrix must contain numeric values")
        if not np.isfinite(matrix).all():
            raise ValueError("keyframe affine matrix must contain finite values")
        if np.linalg.matrix_rank(matrix[:, :2]) < 2:
            raise ValueError(
                "keyframe affine transform must have a non-degenerate linear component"
            )
        owned = np.array(matrix, dtype=np.float64, copy=True)
        owned.setflags(write=False)
        object.__setattr__(self, "matrix", owned)


@dataclass(frozen=True, slots=True)
class AffineTransformTrack:
    """Immutable ordered affine-transform parameter track."""

    keyframes: tuple[AffineTransformKeyframe, ...]

    def __post_init__(self) -> None:
        keyframes = tuple(self.keyframes)
        if len(keyframes) < 2:
            raise ValueError("at least two affine transform keyframes are required")
        if any(
            later.time <= earlier.time
            for earlier, later in zip(keyframes, keyframes[1:])
        ):
            raise ValueError("affine transform keyframe times must be strictly increasing")
        object.__setattr__(self, "keyframes", keyframes)

    def sample(self, time: float) -> AffineTransformSpec:
        """Sample affine parameters at a finite time with endpoint clamping."""
        if not np.isfinite(time):
            raise ValueError("sample time must be finite")
        t = float(time)
        if t <= self.keyframes[0].time:
            return _spec_from_keyframe(self.keyframes[0])
        if t >= self.keyframes[-1].time:
            return _spec_from_keyframe(self.keyframes[-1])

        index = next(
            i
            for i in range(len(self.keyframes) - 1)
            if self.keyframes[i].time <= t <= self.keyframes[i + 1].time
        )
        first, second = self.keyframes[index : index + 2]
        factor = (t - first.time) / (second.time - first.time)
        matrix = first.matrix + factor * (second.matrix - first.matrix)
        return AffineTransformSpec(
            width=1,
            height=1,
            matrix=matrix,
        )


def _spec_from_keyframe(keyframe: AffineTransformKeyframe) -> AffineTransformSpec:
    return AffineTransformSpec(width=1, height=1, matrix=keyframe.matrix)
