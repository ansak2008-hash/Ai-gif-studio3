from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import cv2
import numpy as np
from .camera import CameraState, project_points


@dataclass(frozen=True)
class ManuscriptPlane:
    center: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    half_width: float
    half_height: float

    def local_axes(self) -> tuple[np.ndarray, np.ndarray]:
        n = np.asarray(self.normal, dtype=np.float64)
        n /= np.linalg.norm(n)
        ref = np.array([0.0, 1.0, 0.0]) if abs(n[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        right = np.cross(ref, n)
        right /= np.linalg.norm(right)
        return right, np.cross(n, right)

    def corners_world(self) -> np.ndarray:
        c = np.asarray(self.center, dtype=np.float64)
        right, up = self.local_axes()
        return np.stack([c - self.half_width * right + self.half_height * up,
                         c + self.half_width * right + self.half_height * up,
                         c + self.half_width * right - self.half_height * up,
                         c - self.half_width * right - self.half_height * up])


def homography_from_corners(src_px: np.ndarray, dst_px: np.ndarray) -> np.ndarray:
    src, dst = np.asarray(src_px, np.float32), np.asarray(dst_px, np.float32)
    if src.shape != (4, 2) or dst.shape != (4, 2):
        raise ValueError("corners must have shape (4, 2)")
    return cv2.getPerspectiveTransform(src, dst).astype(np.float64)


def warp_manuscript(manuscript_rgba: np.ndarray, camera: CameraState,
                    plane: ManuscriptPlane, viewport: Tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    src = np.asarray(manuscript_rgba, dtype=np.float32)
    if src.ndim != 3 or src.shape[2] != 4:
        raise ValueError("expected HxWx4 RGBA")
    width, height = viewport
    screen, valid = project_points(camera.view_projection(), plane.corners_world(), viewport)
    if not bool(np.all(valid)):
        raise ValueError("manuscript plane crosses camera near plane")
    h, w = src.shape[:2]
    source = np.array([[0., 0.], [w, 0.], [w, h], [0., h]], dtype=np.float64)
    H = homography_from_corners(source, screen)
    alpha = np.clip(src[..., 3:4], 0., 1.)
    premul = np.concatenate([src[..., :3] * alpha, alpha], axis=-1)
    warped = cv2.warpPerspective(premul.astype(np.float32), H, (width, height),
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(0., 0., 0., 0.))
    out_alpha = np.clip(warped[..., 3:4], 0., 1.)
    rgb = np.divide(warped[..., :3], np.maximum(out_alpha, 1e-8),
                    out=np.zeros_like(warped[..., :3]), where=out_alpha > 1e-8)
    return np.concatenate([np.clip(rgb, 0., 4.), out_alpha], axis=-1).astype(np.float32), out_alpha[..., 0]
