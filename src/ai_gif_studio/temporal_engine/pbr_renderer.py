"""Dedicated renderer boundary for the Phase 3 PBR surface path."""
from __future__ import annotations

import numpy as np

from .camera import CameraModel, CameraState
from .depth_field import DepthField
from .pbr_surface import shade_depth_field_from_camera


def render_pbr_depth_field(
    depth_field: DepthField,
    camera: CameraState | CameraModel,
    surface_points_world: np.ndarray,
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
) -> np.ndarray:
    """Render a canonical DepthField to deterministic linear RGBA.

    This adapter is intentionally separate from the legacy manuscript renderer.
    RGB comes from the PBR surface path; alpha is derived from the canonical
    signed-distance support and remains an output-stage concern.
    """
    rgb = shade_depth_field_from_camera(
        depth_field,
        camera,
        surface_points_world,
        albedo,
        roughness,
        metallic=metallic,
        light=light,
        light_color=light_color,
        light_intensity=light_intensity,
    )
    alpha = (np.asarray(depth_field.distance_px) > 0.0).astype(np.float64)
    return np.concatenate([rgb, alpha[..., None]], axis=-1).astype(np.float32)
