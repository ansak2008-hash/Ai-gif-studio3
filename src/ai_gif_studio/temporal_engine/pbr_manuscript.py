"""PBR integration for the canonical manuscript plane."""
from __future__ import annotations

import numpy as np

from .camera import CameraState
from .depth_field import DepthField
from .manuscript import ManuscriptAsset
from .manuscript_plane import ManuscriptPlane, warp_manuscript
from .pbr_renderer import render_pbr_depth_field


def _world_points_on_plane(
    camera: CameraState,
    plane: ManuscriptPlane,
    viewport: tuple[int, int],
) -> np.ndarray:
    """Intersect one camera ray per viewport pixel with the manuscript plane."""
    width, height = viewport
    if width < 1 or height < 1:
        raise ValueError("viewport dimensions must be positive")

    y, x = np.mgrid[0:height, 0:width]
    ndc_x = (2.0 * (x + 0.5) / width) - 1.0
    ndc_y = 1.0 - (2.0 * (y + 0.5) / height)
    near_clip = np.stack([ndc_x, ndc_y, -np.ones_like(ndc_x), np.ones_like(ndc_x)], axis=-1)
    far_clip = np.stack([ndc_x, ndc_y, np.ones_like(ndc_x), np.ones_like(ndc_x)], axis=-1)

    inverse_vp = np.linalg.inv(camera.view_projection())
    near_world_h = near_clip @ inverse_vp.T
    far_world_h = far_clip @ inverse_vp.T
    near_world = near_world_h[..., :3] / near_world_h[..., 3:4]
    far_world = far_world_h[..., :3] / far_world_h[..., 3:4]

    rays = far_world - near_world
    ray_length = np.linalg.norm(rays, axis=-1, keepdims=True)
    rays /= np.maximum(ray_length, np.finfo(np.float64).eps)

    center = np.asarray(plane.center, dtype=np.float64)
    normal = np.asarray(plane.normal, dtype=np.float64)
    normal /= np.linalg.norm(normal)
    denominator = np.sum(rays * normal, axis=-1)
    numerator = np.sum((center - near_world) * normal, axis=-1)

    if np.any(np.abs(denominator) <= 1e-12):
        raise ValueError("manuscript plane is parallel to one or more camera rays")

    distance = numerator / denominator
    if np.any(distance <= 0.0):
        raise ValueError("manuscript plane lies behind the camera for some pixels")
    return near_world + rays * distance[..., None]


def render_pbr_manuscript(
    asset: ManuscriptAsset,
    camera: CameraState,
    plane: ManuscriptPlane,
    viewport: tuple[int, int],
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
    bevel_width_px: float = 8.0,
    bevel_power: float = 0.75,
    height_scale_px: float = 2.5,
) -> np.ndarray:
    """Render a manuscript plane through the Phase 3 PBR path."""
    width, height = viewport
    _, alpha = warp_manuscript(asset.rgba_linear, camera, plane, viewport)
    field = DepthField.from_alpha(
        alpha,
        bevel_width_px=bevel_width_px,
        bevel_power=bevel_power,
        height_scale_px=height_scale_px,
    )
    points = _world_points_on_plane(camera, plane, viewport)
    return render_pbr_depth_field(
        field,
        camera,
        points,
        albedo,
        roughness,
        metallic=metallic,
        light=light,
        light_color=light_color,
        light_intensity=light_intensity,
    )
