from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class AffineTransform:
    """Readable affine transform with an exact matrix escape hatch for composition."""

    translation_px: tuple[float, float] = (0.0, 0.0)
    scale: tuple[float, float] = (1.0, 1.0)
    rotation_deg: float = 0.0
    pivot_px: tuple[float, float] = (0.0, 0.0)
    opacity: float = 1.0
    _matrix_override: tuple[float, float, float, float, float, float] | None = None

    @classmethod
    def identity(cls) -> AffineTransform:
        return cls()

    def to_matrix(self) -> np.ndarray:
        if self._matrix_override is not None:
            return np.asarray(self._matrix_override, dtype=np.float32).reshape(2, 3).copy()

        sx, sy = self.scale
        tx, ty = self.translation_px
        px, py = self.pivot_px
        c = math.cos(math.radians(self.rotation_deg))
        s = math.sin(math.radians(self.rotation_deg))
        return np.array(
            [
                [sx * c, -sy * s, tx + px - sx * c * px + sy * s * py],
                [sx * s, sy * c, ty + py - sx * s * px - sy * c * py],
            ],
            dtype=np.float32,
        )

    def matrix(self) -> np.ndarray:
        """Backward-compatible alias for :meth:`to_matrix`."""
        return self.to_matrix()

    @classmethod
    def from_matrix(cls, matrix: np.ndarray, opacity: float = 1.0) -> "AffineTransform":
        m = np.asarray(matrix, dtype=np.float64)
        if m.shape == (3, 3):
            if not np.allclose(m[2], (0.0, 0.0, 1.0), atol=1e-6):
                raise ValueError("homogeneous affine matrix must have last row [0, 0, 1]")
            m = m[:2]
        if m.shape != (2, 3) or not np.all(np.isfinite(m)):
            raise ValueError("expected a finite 2x3 or homogeneous 3x3 affine matrix")
        return cls(opacity=float(opacity), _matrix_override=tuple(float(v) for v in m.ravel()))

    @staticmethod
    def compose(first: AffineTransform, second: AffineTransform) -> "AffineTransform":
        """Return the exact transform equivalent to applying first, then second."""
        a = np.vstack([first.to_matrix(), [0.0, 0.0, 1.0]]).astype(np.float64)
        b = np.vstack([second.to_matrix(), [0.0, 0.0, 1.0]]).astype(np.float64)
        return AffineTransform.from_matrix(b @ a, opacity=first.opacity * second.opacity)


def warp_premultiplied_rgba(
    rgba_linear: np.ndarray,
    transform: AffineTransform,
    out_size: tuple[int, int],
) -> np.ndarray:
    """Warp straight-alpha RGBA through premultiplied-alpha sampling.

    The public input and output are straight-alpha RGBA in linear light. The
    intermediate warp is premultiplied to prevent transparent-edge halos.
    """
    src = np.asarray(rgba_linear, dtype=np.float32)
    if src.ndim != 3 or src.shape[2] != 4:
        raise ValueError("expected RGBA float32")
    a = np.clip(src[:, :, 3:4], 0, 1)
    premul = np.concatenate([src[:, :, :3] * a, a], axis=2)
    out_w, out_h = out_size
    warped = cv2.warpAffine(
        premul,
        transform.to_matrix(),
        (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    alpha = np.clip(warped[:, :, 3:4], 0, 1)
    rgb = np.divide(
        warped[:, :, :3],
        np.maximum(alpha, 1e-8),
        where=alpha > 1e-8,
        out=np.zeros_like(warped[:, :, :3]),
    )
    rgb = np.clip(rgb, 0, 1)
    return np.concatenate([rgb, alpha], axis=2)
