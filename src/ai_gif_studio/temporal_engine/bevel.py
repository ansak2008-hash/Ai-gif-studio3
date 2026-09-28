"""Canonical bevel height profiles for manuscript surfaces."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BevelProfile:
    """Deterministic bevel profile defined in pixel-space distance."""

    width_px: float = 8.0
    power: float = 0.75
    smooth: bool = True

    def __post_init__(self) -> None:
        if not np.isfinite(self.width_px) or self.width_px <= 0.0:
            raise ValueError("width_px must be finite and > 0")
        if not np.isfinite(self.power) or self.power <= 0.0:
            raise ValueError("power must be finite and > 0")

    def evaluate(self, distance_px: np.ndarray) -> np.ndarray:
        """Evaluate height [0, 1] from signed distance in pixels."""
        d = np.asarray(distance_px, dtype=np.float32)
        t = np.clip(d / np.float32(self.width_px), 0.0, 1.0)

        if self.smooth:
            u = np.power(t, np.float32(self.power))
            height = u * u * (3.0 - 2.0 * u)
        else:
            height = np.power(t, np.float32(self.power))

        return height.astype(np.float32, copy=False)

    def derivative(self, distance_px: np.ndarray) -> np.ndarray:
        """Closed-form derivative dh/dd in inverse pixels."""
        d = np.asarray(distance_px, dtype=np.float32)
        t = np.clip(d / np.float32(self.width_px), 0.0, 1.0)
        p = np.float32(self.power)

        if not self.smooth:
            safe_t = np.maximum(t, np.float32(1e-6))
            deriv = p * np.power(safe_t, p - 1.0) / np.float32(self.width_px)
            deriv = np.where((t <= 0.0) | (t >= 1.0), 0.0, deriv)
            return deriv.astype(np.float32)

        u = np.power(t, p)
        du_dd = np.where(
            t > 0.0,
            p * np.power(np.maximum(t, np.float32(1e-6)), p - 1.0)
            / np.float32(self.width_px),
            0.0,
        )
        deriv = 6.0 * u * (1.0 - u) * du_dd
        deriv = np.where((t <= 0.0) | (t >= 1.0), 0.0, deriv)
        return deriv.astype(np.float32)
