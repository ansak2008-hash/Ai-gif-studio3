"""Sequence orchestration for the isolated manuscript motion layer."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .manuscript import ManuscriptAsset
from .manuscript_plane import ManuscriptPlane
from .material_pbr import DirectLight, PBRMaterial
from .motion import CameraMotionTrack
from .pbr_manuscript import render_pbr_manuscript
from .timeline import AnimationTimeline


@dataclass(frozen=True)
class PBRMotionRenderer:
    timeline: AnimationTimeline
    motion: CameraMotionTrack
    viewport: tuple[int, int]

    def __post_init__(self) -> None:
        if self.viewport[0] < 1 or self.viewport[1] < 1:
            raise ValueError("viewport dimensions must be positive")

    def render_sequence(
        self,
        asset: ManuscriptAsset,
        plane: ManuscriptPlane,
        albedo: np.ndarray | list[float],
        roughness: float,
        metallic: float = 0.0,
        light: np.ndarray | tuple[float, float, float] = (0.0, 0.0, 1.0),
        light_color: np.ndarray | list[float] | float = 1.0,
        light_intensity: float = 1.0,
        *,
        material: PBRMaterial | None = None,
        lights: tuple[DirectLight, ...] | list[DirectLight] | None = None,
    ) -> tuple[list[np.ndarray], tuple[int, ...]]:
        frames = [
            render_pbr_manuscript(
                asset,
                self.motion.sample(timing.timestamp_sec),
                plane,
                self.viewport,
                albedo,
                roughness,
                metallic=metallic,
                light=light,
                light_color=light_color,
                light_intensity=light_intensity,
                material=material,
                lights=lights,
            )
            for timing in self.timeline.timings()
        ]
        return frames, self.timeline.centisecond_delays()
