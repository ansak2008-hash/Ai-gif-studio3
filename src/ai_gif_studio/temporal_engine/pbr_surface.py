"""Depth-field to PBR surface shading integration."""
from __future__ import annotations

import numpy as np

from .camera import CameraModel, CameraState
from .depth_field import DepthField
from .material_pbr import DirectLight, PBRMaterial, shade_pbr, shade_pbr_lights

_DEFAULT_LIGHT = DirectLight(direction=(0.0, 0.0, 1.0))


def shade_depth_field(
    depth_field: DepthField,
    view: np.ndarray,
    light: np.ndarray,
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
    *,
    material: PBRMaterial | None = None,
    lights: tuple[DirectLight, ...] | list[DirectLight] | None = None,
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

    active_material = material or PBRMaterial(
        albedo=tuple(np.asarray(albedo, dtype=np.float64).tolist()),
        roughness=roughness,
        metallic=metallic,
    )
    active_lights = tuple(lights) if lights is not None else (
        DirectLight(
            direction=tuple(np.asarray(light, dtype=np.float64).tolist()),
            color=tuple(np.broadcast_to(np.asarray(light_color, dtype=np.float64), (3,)).tolist()),
            intensity=light_intensity,
        ),
    )
    rgb = shade_pbr_lights(normals, view, active_lights, active_material)
    surface = distance > 0.0
    return np.where(surface[..., None], rgb, 0.0).astype(np.float64)


def _image_normals_to_world(
    normals_image: np.ndarray,
    camera_state: CameraState,
) -> np.ndarray:
    """Map image-plane normals (x=right, y=down, z=toward camera) to world."""
    normals = np.asarray(normals_image, dtype=np.float64)
    if normals.ndim != 3 or normals.shape[-1] != 3:
        raise ValueError("normals must have shape (H, W, 3)")
    view = camera_state.view_matrix()
    right = view[0, :3]
    up = view[1, :3]
    toward_camera = view[2, :3]
    basis = np.stack([right, -up, toward_camera], axis=1)
    world = normals @ basis.T
    length = np.linalg.norm(world, axis=-1, keepdims=True)
    return world / np.maximum(length, np.finfo(np.float64).eps)


def shade_depth_field_from_camera(
    depth_field: DepthField,
    camera: CameraState | CameraModel,
    surface_points_world: np.ndarray,
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
    *,
    material: PBRMaterial | None = None,
    lights: tuple[DirectLight, ...] | list[DirectLight] | None = None,
) -> np.ndarray:
    """Shade a DepthField using per-pixel view directions from a camera.

    surface_points_world must be the canonical world-space surface positions
    corresponding to the DepthField pixels. Camera projection math is not
    modified; only the camera position is used to derive V = normalize(C-P).
    """
    if isinstance(camera, CameraModel):
        camera_position = np.asarray(camera.state.position, dtype=np.float64)
    elif isinstance(camera, CameraState):
        camera_position = np.asarray(camera.position, dtype=np.float64)
    else:
        raise TypeError("camera must be CameraState or CameraModel")

    points = np.asarray(surface_points_world, dtype=np.float64)
    if points.shape != (*depth_field.distance_px.shape, 3):
        raise ValueError("surface_points_world must have shape (H, W, 3)")

    state = camera.state if isinstance(camera, CameraModel) else camera
    world_normals = _image_normals_to_world(depth_field.normals, state)
    view = camera_position - points
    # The camera path uses the canonical world-space surface points and the
    # camera position only; no depth-derived normal reconstruction occurs here.
    active_material = material or PBRMaterial(
        albedo=tuple(np.asarray(albedo, dtype=np.float64).tolist()),
        roughness=roughness,
        metallic=metallic,
    )
    active_lights = tuple(lights) if lights is not None else (
        DirectLight(
            direction=tuple(np.asarray(light, dtype=np.float64).tolist()),
            color=tuple(np.broadcast_to(np.asarray(light_color, dtype=np.float64), (3,)).tolist()),
            intensity=light_intensity,
        ),
    )
    shaded = shade_pbr_lights(world_normals, view, active_lights, active_material)
    surface = np.asarray(depth_field.distance_px) > 0.0
    return np.where(surface[..., None], shaded, 0.0).astype(np.float64)
