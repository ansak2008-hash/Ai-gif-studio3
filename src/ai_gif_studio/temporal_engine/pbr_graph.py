"""RenderGraph adapter for deterministic direct-light PBR shading."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .material_pbr import DirectLight, PBRMaterial, shade_pbr
from .render_buffer import RenderBuffer


@dataclass(frozen=True, slots=True)
class PBRDirectLightNode:
    """Adapt the existing float64 direct-light PBR kernel to RenderBuffer."""

    normals: np.ndarray
    views: np.ndarray
    material: PBRMaterial
    lights: tuple[DirectLight, ...] | list[DirectLight]

    def __post_init__(self) -> None:
        normals = self._freeze_vectors(self.normals, "normals")
        views = self._freeze_vectors(self.views, "views")
        if normals.shape != views.shape:
            raise ValueError("normals and views must have identical shapes")
        if not isinstance(self.material, PBRMaterial):
            raise TypeError("material must be a PBRMaterial")
        lights = tuple(self.lights)
        if not lights:
            raise ValueError("lights must contain at least one DirectLight")
        if any(not isinstance(light, DirectLight) for light in lights):
            raise TypeError("lights must contain DirectLight values")
        object.__setattr__(self, "normals", normals)
        object.__setattr__(self, "views", views)
        object.__setattr__(self, "lights", lights)

    @staticmethod
    def _freeze_vectors(value: np.ndarray, name: str) -> np.ndarray:
        vectors = np.array(value, dtype=np.float64, copy=True)
        if vectors.ndim != 3 or vectors.shape[-1] != 3:
            raise ValueError(f"{name} must have shape HxWx3")
        if vectors.shape[0] < 1 or vectors.shape[1] < 1:
            raise ValueError(f"{name} dimensions must be positive")
        if not np.isfinite(vectors).all():
            raise ValueError(f"{name} must contain finite values")
        lengths = np.linalg.norm(vectors, axis=-1)
        if np.any(lengths <= np.finfo(np.float64).eps):
            raise ValueError(f"{name} must contain non-zero vectors")
        vectors.setflags(write=False)
        return vectors

    def process(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        """Shade one RenderBuffer with ordered direct lights."""
        if len(inputs) != 1:
            raise ValueError("PBRDirectLightNode requires exactly one RenderBuffer input")
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("PBRDirectLightNode input must be a RenderBuffer")
        if source.shape[:2] != self.normals.shape[:2]:
            raise ValueError("PBR geometry dimensions must match RenderBuffer dimensions")

        albedo = np.asarray(self.material.albedo, dtype=np.float64)
        result = np.zeros(source.data.shape[:2] + (3,), dtype=np.float64)
        for light in self.lights:
            result += shade_pbr(
                self.normals,
                self.views,
                np.asarray(light.direction, dtype=np.float64),
                albedo,
                self.material.roughness,
                metallic=self.material.metallic,
                light_color=np.asarray(light.color, dtype=np.float64),
                light_intensity=light.intensity,
            )

        if not np.isfinite(result).all() or np.any(result < 0.0):
            raise ValueError("PBR direct-light output must be finite and non-negative")

        output = np.concatenate(
            [result.astype(np.float32), source.data[..., 3:4]],
            axis=-1,
        )
        return RenderBuffer.from_linear_rgba(output)
