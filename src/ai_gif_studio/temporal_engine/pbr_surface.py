"""Depth-field to PBR surface shading integration."""
from __future__ import annotations

import numpy as np

from .depth_field import DepthField
from .material_pbr import shade_pbr


def shade_depth_field(
    depth_field: DepthField,
    view: np.ndarray,
    light: np.ndarray,
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
) -> np.ndarray:
    """Shade a canonical DepthField without recomputing its surface normals.

    The DepthField owns the geometry. Its signed distance selects the rendered
    surface, while its stored unit normals are passed directly to the PBR
    shader. The result is deterministic linear RGB with shape (H, W, 3).
    """
    if not isinstance(depth_field, DepthField):
        raise TypeError("depth_field must be a DepthField")

    distance = np.asarray(depth_field.distance_px, dtype=np.float64)
    normals = np.asarray(depth_field.normals, dtype=np.float64)
    if distance.ndim != 2:
        raise ValueError("depth_field.distance_px must be 2D")
    if normals.shape != (*distance.shape, 3):
        raise ValueError("depth_field.normals must have shape (H, W, 3)")

    rgb = shade_pbr(
        normals,
        view,
        light,
        albedo,
        roughness,
        metallic=metallic,
        light_color=light_color,
        light_intensity=light_intensity,
    )
    surface = distance > 0.0
    return np.where(surface[..., None], rgb, 0.0).astype(np.float64)
