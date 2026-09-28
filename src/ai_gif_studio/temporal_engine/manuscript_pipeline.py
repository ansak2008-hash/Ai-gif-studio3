"""Final Phase 6 manuscript rendering and export pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .color_export import ExportColorSpec
from .encoder import encode_linear_gif
from .manuscript import ManuscriptAsset
from .manuscript_plane import ManuscriptPlane
from .motion import CameraMotionTrack
from .pbr_motion import PBRMotionRenderer
from .quality import TemporalValidation, validate_temporal_sequence
from .timeline import AnimationTimeline


@dataclass(frozen=True)
class ManuscriptPipeline:
    """End-to-end deterministic motion → PBR → color → GIF pipeline."""

    timeline: AnimationTimeline
    motion: CameraMotionTrack
    viewport: tuple[int, int]
    color_spec: ExportColorSpec | None = None

    def __post_init__(self) -> None:
        if self.viewport[0] < 1 or self.viewport[1] < 1:
            raise ValueError("viewport dimensions must be positive")
        if self.color_spec is None:
            object.__setattr__(self, "color_spec", ExportColorSpec())

    def render_frames(
        self,
        asset: ManuscriptAsset,
        plane: ManuscriptPlane,
        albedo: np.ndarray | list[float],
        roughness: float,
        metallic: float = 0.0,
        light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
        light_color: np.ndarray | list[float] | float = 1.0,
        light_intensity: float = 1.0,
    ) -> tuple[list[np.ndarray], tuple[int, ...], TemporalValidation]:
        renderer = PBRMotionRenderer(self.timeline, self.motion, self.viewport)
        frames, delays = renderer.render_sequence(
            asset,
            plane,
            albedo,
            roughness,
            metallic=metallic,
            light=light,
            light_color=light_color,
            light_intensity=light_intensity,
        )
        validation = validate_temporal_sequence(frames)
        if not validation.passed:
            raise ValueError(
                f"temporal quality gate failed at frame {validation.spike_index}"
            )
        return frames, delays, validation

    def render_to_gif(
        self,
        asset: ManuscriptAsset,
        plane: ManuscriptPlane,
        output: Path | str,
        albedo: np.ndarray | list[float],
        roughness: float,
        metallic: float = 0.0,
        light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
        light_color: np.ndarray | list[float] | float = 1.0,
        light_intensity: float = 1.0,
    ) -> str:
        frames, delays, _ = self.render_frames(
            asset,
            plane,
            albedo,
            roughness,
            metallic=metallic,
            light=light,
            light_color=light_color,
            light_intensity=light_intensity,
        )
        return encode_linear_gif(frames, delays, output, self.color_spec)
