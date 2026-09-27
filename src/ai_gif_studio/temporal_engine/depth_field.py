"""Canonical signed distance, bevel height, and deterministic surface normals."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .bevel import BevelProfile


@dataclass(frozen=True)
class DepthField:
    """Single canonical depth representation shared by later render stages.

    distance_px is a true signed distance approximation:
    positive inside the alpha silhouette and negative outside.
    height is a dimensionless bevel profile in [0, 1].
    normals are unit surface normals for z = height * height_scale_px,
    expressed in the image-plane coordinate system.
    """

    distance_px: np.ndarray
    height: np.ndarray
    normals: np.ndarray

    @classmethod
    def from_alpha(
        cls,
        alpha: np.ndarray,
        bevel_width_px: float = 8.0,
        bevel_power: float = 0.75,
        height_scale_px: float = 2.5,
        alpha_threshold: float = 0.5,
        smooth: bool = True,
    ) -> "DepthField":
        """Build a deterministic canonical field from an alpha mask.

        The signed distance is constructed from inside/outside Euclidean
        distance transforms.  The bevel profile is evaluated analytically
        from signed distance, while the distance-field direction is obtained
        from centered differences of the sampled SDF.  Thus the chain rule is
        explicit and the bevel derivative is closed-form; the discrete SDF
        itself remains a sampled numerical field.
        """
        a = np.clip(np.asarray(alpha, dtype=np.float32), 0.0, 1.0)
        if a.ndim != 2:
            raise ValueError("alpha must be 2D")
        if not 0.0 < alpha_threshold < 1.0:
            raise ValueError("alpha_threshold must be in (0, 1)")
        if not np.isfinite(height_scale_px) or height_scale_px <= 0.0:
            raise ValueError("height_scale_px must be finite and > 0")

        bevel = BevelProfile(
            width_px=float(bevel_width_px),
            power=float(bevel_power),
            smooth=smooth,
        )

        mask = (a >= np.float32(alpha_threshold)).astype(np.uint8)
        inside = cv2.distanceTransform(mask, cv2.DIST_L2, 5).astype(np.float32)
        outside = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5).astype(
            np.float32
        )
        signed = inside - outside

        # The canonical surface exists only on the alpha support.  The signed
        # distance is retained everywhere because later DOF/reveal stages need
        # a continuous inside/outside depth reference.
        height = bevel.evaluate(signed)
        height = np.where(mask > 0, height, 0.0).astype(np.float32)

        # Chain rule:
        #   grad(h) = f'(d) * grad(d)
        # The profile derivative is closed-form.  grad(d) is the centered
        # finite-difference gradient of the sampled Euclidean SDF.
        grad_d_y, grad_d_x = np.gradient(signed.astype(np.float64), edge_order=1)
        grad_d_x = grad_d_x.astype(np.float32)
        grad_d_y = grad_d_y.astype(np.float32)

        grad_len = np.sqrt(grad_d_x * grad_d_x + grad_d_y * grad_d_y)
        safe_len = np.maximum(grad_len, np.float32(1e-6))
        grad_d_x = grad_d_x / safe_len
        grad_d_y = grad_d_y / safe_len

        dh_dd = bevel.derivative(signed)
        dh_dx = dh_dd * grad_d_x
        dh_dy = dh_dd * grad_d_y

        # height_scale_px converts dimensionless height into a z displacement
        # measured in the same pixel coordinate units as x/y.
        dz_dx = dh_dx * np.float32(height_scale_px)
        dz_dy = dh_dy * np.float32(height_scale_px)

        nx = -dz_dx
        ny = -dz_dy
        nz = np.ones_like(height, dtype=np.float32)
        norm = np.sqrt(nx * nx + ny * ny + nz * nz)
        normals = np.stack(
            [nx / norm, ny / norm, nz / norm],
            axis=-1,
        ).astype(np.float32)

        # Transparent pixels are not a rendered surface. Keep their normal
        # canonical and deterministic so downstream samplers never see NaNs.
        normals = np.where(
            (mask > 0)[..., np.newaxis],
            normals,
            np.array([0.0, 0.0, 1.0], dtype=np.float32),
        ).astype(np.float32)

        return cls(
            distance_px=signed.astype(np.float32),
            height=height,
            normals=normals,
        )
