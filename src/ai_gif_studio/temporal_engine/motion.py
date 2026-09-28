"""Deterministic motion separation for the Phase 3 manuscript renderer."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .camera import CameraState


def smoothstep01(value: float) -> float:
    """Cubic ease-in/ease-out over a clamped [0, 1] interval."""
    t = float(value)
    if not np.isfinite(t):
        raise ValueError("motion progress must be finite")
    t = float(np.clip(t, 0.0, 1.0))
    return t * t * (3.0 - 2.0 * t)


@dataclass(frozen=True)
class MotionKeyframe:
    time_sec: float
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    roll_deg: float = 0.0

    def __post_init__(self) -> None:
        values = (*self.position, *self.target, self.time_sec, self.roll_deg)
        if not all(np.isfinite(float(value)) for value in values):
            raise ValueError("motion keyframe values must be finite")


@dataclass(frozen=True)
class CameraMotionTrack:
    """Interpolates camera motion without owning rendering or material state."""

    keyframes: tuple[MotionKeyframe, ...]
    fov_y_deg: float = 45.0
    aspect: float = 1.0
    near: float = 0.01
    far: float = 10000.0
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)

    def __post_init__(self) -> None:
        if not self.keyframes:
            raise ValueError("motion track requires at least one keyframe")
        if any(
            later.time_sec <= earlier.time_sec
            for earlier, later in zip(self.keyframes, self.keyframes[1:])
        ):
            raise ValueError("motion keyframe times must be strictly increasing")
        if not 0.0 < self.fov_y_deg < 180.0 or self.aspect <= 0.0:
            raise ValueError("invalid camera projection settings")
        if self.near <= 0.0 or self.far <= self.near:
            raise ValueError("invalid camera clip planes")

    @property
    def duration_sec(self) -> float:
        return self.keyframes[-1].time_sec

    def sample(self, time_sec: float) -> CameraState:
        if not np.isfinite(time_sec):
            raise ValueError("time_sec must be finite")
        t = float(time_sec)
        if t <= self.keyframes[0].time_sec:
            key = self.keyframes[0]
            return self._state(key.position, key.target, key.roll_deg)
        if t >= self.keyframes[-1].time_sec:
            key = self.keyframes[-1]
            return self._state(key.position, key.target, key.roll_deg)

        index = next(
            i
            for i in range(len(self.keyframes) - 1)
            if self.keyframes[i].time_sec <= t <= self.keyframes[i + 1].time_sec
        )
        first, second = self.keyframes[index : index + 2]
        u = smoothstep01(
            (t - first.time_sec) / (second.time_sec - first.time_sec)
        )
        position = tuple(
            float(a + (b - a) * u) for a, b in zip(first.position, second.position)
        )
        target = tuple(
            float(a + (b - a) * u) for a, b in zip(first.target, second.target)
        )
        roll = first.roll_deg + (second.roll_deg - first.roll_deg) * u
        return self._state(position, target, roll)

    def _state(
        self,
        position: tuple[float, float, float],
        target: tuple[float, float, float],
        roll_deg: float,
    ) -> CameraState:
        return CameraState(
            position=position,
            target=target,
            up=self.up,
            fov_y_deg=self.fov_y_deg,
            aspect=self.aspect,
            near=self.near,
            far=self.far,
            roll_deg=float(roll_deg),
        )
