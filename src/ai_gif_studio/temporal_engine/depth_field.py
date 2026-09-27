"""Canonical alpha-derived depth, bevel height and analytical normals."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class DepthField:
    distance_px: np.ndarray
    height: np.ndarray
    normals: np.ndarray

    @classmethod
    def from_alpha(
        cls,
        alpha: np.ndarray,
        bevel_width_px: float = 8.0,
        bevel_power: float = 0.75,
    ) -> "DepthField":
        a = np.clip(np.asarray(alpha, dtype=np.float32), 0.0, 1.0)
        if a.ndim != 2:
            raise ValueError("alpha must be 2D")
        if bevel_width_px <= 0 or bevel_power <= 0:
            raise ValueError("invalid bevel parameters")

        mask = (a > 0.5).astype(np.uint8)
        inside = cv2.distanceTransform(mask, cv2.DIST_L2, 5).astype(np.float32)
        outside = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5).astype(np.float32)
        signed = inside - outside  # > 0 inside, < 0 outside

        # Map [-bevel_width, +bevel_width] -> [0, 1].
        t = np.clip(
            (signed + bevel_width_px) / (2.0 * bevel_width_px),
            0.0,
            1.0,
        )
        h = np.power(t, bevel_power).astype(np.float32)

        # Zero outside alpha support (prevents bleed into transparent regions).
        h = h * (a > 0.0).astype(np.float32)

        # Analytical normals from heightmap, scaled to physical slope.
        gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8.0
        gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8.0
        nx = -gx * bevel_width_px
        ny = -gy * bevel_width_px
        nz = np.ones_like(h)
        norm = np.sqrt(nx * nx + ny * ny + nz * nz)
        normals = np.stack(
            [nx / norm, ny / norm, nz / norm],
            axis=-1,
        ).astype(np.float32)

        return cls(signed, h, normals)
