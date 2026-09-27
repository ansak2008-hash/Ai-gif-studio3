from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .cinematic_camera import CameraKey, CinematicCamera
from .glint import GlintParameters, gaussian_glint
from .material import Material, MaterialSpec, material_preset, shade_metallic
from .manuscript import ManuscriptAsset
from .particles import ParticleField, render_particles
from .reveal import bloom, edge_reveal


@dataclass(frozen=True)
class ManuscriptCinematicProfile:
    duration_sec: float = 9.5
    fps: float = 30.0
    canvas: tuple[int, int] = (1280, 720)
    reveal_end: float = 1.5
    transform_end: float = 3.5
    macro_end: float = 7.0
    hero_end: float = 9.5
    zoom_max: float = 3.5
    glint_angle_deg: float = 35.0
    glint_sigma: float = 25.0
    glint_peak: float = 2.55

    def __post_init__(self):
        if self.duration_sec <= 0 or self.fps <= 0:
            raise ValueError("duration and fps must be positive")
        if not (
            0
            < self.reveal_end
            < self.transform_end
            < self.macro_end
            <= self.hero_end
            <= self.duration_sec
        ):
            raise ValueError("invalid cinematic phase boundaries")
        if self.canvas[0] < 1 or self.canvas[1] < 1:
            raise ValueError("invalid canvas")
        if self.zoom_max < 1:
            raise ValueError("zoom_max must be >= 1")


@dataclass
class ManuscriptCinematicRenderer:
    profile: ManuscriptCinematicProfile = ManuscriptCinematicProfile()
    material: MaterialSpec = material_preset(Material.GOLD)

    def camera_key(self, t: float) -> CameraKey:
        p = self.profile
        t = max(0.0, min(p.duration_sec, float(t)))
        if t <= p.reveal_end:
            s, rx, ry, rz = 1.0, 0.0, 0.0, 0.0
        elif t <= p.transform_end:
            u = (t - p.reveal_end) / (p.transform_end - p.reveal_end)
            e = u * u * (3 - 2 * u)
            s = 1.0 + (1.25 - 1.0) * e
            rx = 0
            ry = 15 * e
            rz = 0
        elif t <= p.macro_end:
            u = (t - p.transform_end) / (p.macro_end - p.transform_end)
            e = u * u * (3 - 2 * u)
            s = 1.25 + (p.zoom_max - 1.25) * e
            rx = 20 * e
            ry = 15
            rz = -10 * e
        else:
            u = (t - p.macro_end) / (p.hero_end - p.macro_end)
            e = u * u * (3 - 2 * u)
            s = p.zoom_max + (1.10 - p.zoom_max) * e
            rx = 20 * (1 - e)
            ry = 15 * (1 - e)
            rz = -10 * (1 - e)
        return CameraKey(t, s, rx, ry, rz, 0, 0)

    def render_frame(self, asset: ManuscriptAsset, t: float) -> np.ndarray:
        p = self.profile
        cam = CinematicCamera(*p.canvas)
        key = self.camera_key(t)
        warped = cam.warp(asset.rgba_linear, key)
        alpha = warped[..., 3]
        shaded = shade_metallic(warped[..., :3], alpha, self.material)
        glint_pos = -3.0 * max(p.canvas)
        if p.duration_sec:
            glint_pos += 10.0 * max(p.canvas) * min(1.0, t / p.duration_sec)
        gl = gaussian_glint(
            p.canvas[::-1],
            GlintParameters(
                glint_pos,
                p.glint_sigma,
                p.glint_peak,
                math.radians(p.glint_angle_deg),
            ),
            alpha,
            (p.canvas[0] / 2, p.canvas[1] / 2),
        )
        out = np.clip(shaded + gl, 0, 4)
        out += render_particles(
            (p.canvas[1], p.canvas[0]),
            ParticleField(p.particle_count, p.particle_seed),
            t,
            key.scale,
        )
        if t <= p.reveal_end:
            out += edge_reveal(alpha, t / p.reveal_end)
        out = bloom(out, threshold=1.0, sigma=5.0, strength=0.22)
        return np.concatenate(
            [np.clip(out, 0, 4), alpha[..., None]], axis=-1
        ).astype(np.float32)

    def render_sequence(self, asset: ManuscriptAsset) -> list[np.ndarray]:
        n = max(1, int(round(self.profile.duration_sec * self.profile.fps)))
        return [self.render_frame(asset, i / self.profile.fps) for i in range(n)]
