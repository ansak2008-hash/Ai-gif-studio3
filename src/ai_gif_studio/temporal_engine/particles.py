"""Deterministic particle field and efficient local Gaussian renderer."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ParticleField:
    count: int = 90
    seed: int = 20260927
    max_radius: float = 3.0

    def __post_init__(self) -> None:
        if self.count < 0 or self.max_radius < 0:
            raise ValueError("invalid particle field")

    def points(self, width: int, height: int) -> tuple[np.ndarray, ...]:
        if width < 1 or height < 1:
            raise ValueError("particle field dimensions must be positive")
        rng = np.random.default_rng(self.seed)
        xy = rng.random((self.count, 2), dtype=np.float32) * np.array(
            [width, height], dtype=np.float32
        )
        depth = rng.random(self.count, dtype=np.float32)
        radius = (0.5 + depth * self.max_radius).astype(np.float32)
        phase = rng.random(self.count, dtype=np.float32) * np.float32(2 * np.pi)
        return xy, depth, radius, phase


def render_particles(
    shape: tuple[int, int],
    field: ParticleField,
    time: float,
    camera_scale: float = 1.0,
) -> np.ndarray:
    h, w = shape
    if h < 1 or w < 1:
        raise ValueError("particle render dimensions must be positive")

    out = np.zeros((h, w, 3), np.float32)
    xy, depth, radius, phase = field.points(w, h)

    for (x, y), d, r, p in zip(xy, depth, radius, phase):
        parallax = (0.15 + 0.85 * d) * max(camera_scale - 1.0, 0.0)
        px = x + (x - w / 2.0) * parallax * 0.10 + math.cos(
            float(p + time * 0.7)
        ) * (1.0 + d * 2.0)
        py = y + (y - h / 2.0) * parallax * 0.06 + math.sin(
            float(p + time * 0.55)
        ) * (1.0 + d * 1.5)
        sigma = max(0.5, float(r) * (0.6 + 0.8 * d))

        # A 6-sigma Gaussian contains all but ~2e-9 of the 1D tail.
        extent = max(1, int(math.ceil(6.0 * sigma)))
        x0 = max(0, int(math.floor(px)) - extent)
        x1 = min(w, int(math.floor(px)) + extent + 1)
        y0 = max(0, int(math.floor(py)) - extent)
        y1 = min(h, int(math.floor(py)) + extent + 1)
        if x0 >= x1 or y0 >= y1:
            continue

        xx = np.arange(x0, x1, dtype=np.float32)[None, :]
        yy = np.arange(y0, y1, dtype=np.float32)[:, None]
        blob = np.exp(
            -((xx - np.float32(px)) ** 2 + (yy - np.float32(py)) ** 2)
            / np.float32(2.0 * sigma * sigma)
        ).astype(np.float32)
        intensity = np.float32(
            (0.04 + 0.16 * d) * (0.7 + 0.3 * math.sin(float(p + time * 1.2)))
        )
        out[y0:y1, x0:x1] += blob[..., None] * intensity

    return out
