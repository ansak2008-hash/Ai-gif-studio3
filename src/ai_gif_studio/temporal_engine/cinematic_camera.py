"""LEGACY: cinematic camera compatibility shim for manuscript rendering.

This module bridges legacy cinematic rendering to the Phase 2 perspective
foundation. Do not extend or import it from new Phase 3 code.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .camera import CameraState
from .manuscript_plane import ManuscriptPlane, warp_manuscript

def smoothstep01(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

@dataclass(frozen=True)
class CameraKey:
    time: float
    scale: float
    rotate_x_deg: float = 0.0
    rotate_y_deg: float = 0.0
    rotate_z_deg: float = 0.0
    x: float = 0.0
    y: float = 0.0

@dataclass(frozen=True)
class CinematicCamera:
    width: int = 1280
    height: int = 720
    perspective_strength: float = 1.0
    fov_y_deg: float = 45.0

    def sample(self, keys: tuple[CameraKey, ...], time: float) -> CameraKey:
        if not keys:
            raise ValueError("camera requires at least one key")
        if any(k.time < 0 for k in keys) or any(b.time <= a.time for a, b in zip(keys, keys[1:])):
            raise ValueError("camera key times must be strictly increasing")
        if time <= keys[0].time:
            return keys[0]
        if time >= keys[-1].time:
            return keys[-1]
        i = next(i for i in range(len(keys) - 1) if keys[i].time <= time <= keys[i + 1].time)
        a, b = keys[i], keys[i + 1]
        e = smoothstep01((time - a.time) / (b.time - a.time))
        return CameraKey(time, a.scale + (b.scale-a.scale)*e,
                         a.rotate_x_deg + (b.rotate_x_deg-a.rotate_x_deg)*e,
                         a.rotate_y_deg + (b.rotate_y_deg-a.rotate_y_deg)*e,
                         a.rotate_z_deg + (b.rotate_z_deg-a.rotate_z_deg)*e,
                         a.x + (b.x-a.x)*e, a.y + (b.y-a.y)*e)

    def state_for_key(self, key: CameraKey, aspect: float | None = None) -> CameraState:
        aspect = self.width / self.height if aspect is None else float(aspect)
        scale = max(float(key.scale), 1e-4)
        distance = 1.20710678 / scale
        rx, ry = math.radians(key.rotate_x_deg), math.radians(key.rotate_y_deg)
        position = np.array([0.0, 0.0, distance], dtype=np.float64)
        cy, sy = math.cos(ry), math.sin(ry)
        position = np.array([cy*position[0] + sy*position[2], position[1],
                             -sy*position[0] + cy*position[2]])
        cx, sx = math.cos(rx), math.sin(rx)
        position = np.array([position[0], cx*position[1] - sx*position[2],
                             sx*position[1] + cx*position[2]])
        target = np.array([key.x/640.0, -key.y/360.0, 0.0])
        return CameraState(tuple(position), tuple(target), (0.0, 1.0, 0.0),
                           self.fov_y_deg, aspect, roll_deg=key.rotate_z_deg)

    def matrix(self, key: CameraKey) -> np.ndarray:
        return self.state_for_key(key).view_projection()

    def warp(self, rgba_linear: np.ndarray, key: CameraKey) -> np.ndarray:
        src = np.asarray(rgba_linear, dtype=np.float32)
        if src.ndim != 3 or src.shape[2] != 4:
            raise ValueError("expected RGBA")
        h, w = src.shape[:2]
        m = float(max(h, w))
        plane = ManuscriptPlane((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), w/m, h/m)
        return warp_manuscript(src, self.state_for_key(key), plane, (self.width, self.height))[0]
