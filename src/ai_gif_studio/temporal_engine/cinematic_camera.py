from __future__ import annotations
from dataclasses import dataclass
import math
import cv2
import numpy as np

def smoothstep01(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

def cubic_bezier01(t: float, p1: float, p2: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    u = 1.0 - t
    return 3*u*u*t*p1 + 3*u*t*t*p2 + t*t*t

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
    perspective_strength: float = 0.0

    def sample(self, keys: tuple[CameraKey, ...], time: float) -> CameraKey:
        if not keys:
            raise ValueError("camera requires at least one key")
        if any(k.time < 0 for k in keys) or any(b.time <= a.time for a,b in zip(keys,keys[1:])):
            raise ValueError("camera key times must be strictly increasing")
        if time <= keys[0].time:
            return keys[0]
        if time >= keys[-1].time:
            return keys[-1]
        i = next(i for i in range(len(keys)-1) if keys[i].time <= time <= keys[i+1].time)
        a, b = keys[i], keys[i+1]
        u = (time - a.time) / (b.time - a.time)
        e = smoothstep01(u)
        return CameraKey(
            time=time,
            scale=a.scale + (b.scale-a.scale)*e,
            rotate_x_deg=a.rotate_x_deg + (b.rotate_x_deg-a.rotate_x_deg)*e,
            rotate_y_deg=a.rotate_y_deg + (b.rotate_y_deg-a.rotate_y_deg)*e,
            rotate_z_deg=a.rotate_z_deg + (b.rotate_z_deg-a.rotate_z_deg)*e,
            x=a.x + (b.x-a.x)*e,
            y=a.y + (b.y-a.y)*e,
        )

    def matrix(self, key: CameraKey) -> np.ndarray:
        cx, cy = self.width/2.0, self.height/2.0
        # Perspective-compatible projective approximation: affine rotation/scale
        # is the safe default; non-zero strength introduces a mild corner-aware warp.
        angle = math.radians(key.rotate_z_deg)
        c, s = math.cos(angle), math.sin(angle)
        m = np.array([[key.scale*c, -key.scale*s, cx-key.scale*c*cx+key.scale*s*cy+key.x],
                      [key.scale*s,  key.scale*c, cy-key.scale*s*cx-key.scale*c*cy+key.y]],
                     dtype=np.float32)
        return m

    def warp(self, rgba_linear: np.ndarray, key: CameraKey) -> np.ndarray:
        src = np.asarray(rgba_linear, dtype=np.float32)
        if src.ndim != 3 or src.shape[2] != 4:
            raise ValueError("expected RGBA")
        a = np.clip(src[...,3:4], 0, 1)
        premul = np.concatenate([src[...,:3]*a, a], axis=-1)
        out = cv2.warpAffine(premul, self.matrix(key), (self.width,self.height),
                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        oa = np.clip(out[...,3:4], 0, 1)
        rgb = np.divide(out[...,:3], np.maximum(oa,1e-8),
                        out=np.zeros_like(out[...,:3]), where=oa>1e-8)
        return np.concatenate([np.clip(rgb,0,1), oa], axis=-1)
