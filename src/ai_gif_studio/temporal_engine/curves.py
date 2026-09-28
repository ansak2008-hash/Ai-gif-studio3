from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class InterpolatorType(StrEnum):
    LINEAR = "linear"
    CUBIC_BEZIER = "cubic_bezier"
    HARMONIC = "harmonic"


class LoopMode(StrEnum):
    LOOP = "loop"
    PING_PONG = "ping_pong"
    HOLD = "hold"
    CLAMP = "clamp"


class RotationMode(StrEnum):
    SHORTEST = "shortest"
    FORWARD = "forward"
    PRESERVE_TURNS = "preserve_turns"

@dataclass(frozen=True)
class Keyframe:
    time: float
    value: float
    control_points: tuple[float, float, float, float] | None = None

@dataclass(frozen=True)
class MotionCurve:
    keyframes: tuple[Keyframe, ...]
    loop_mode: LoopMode = LoopMode.LOOP
    interpolator: InterpolatorType = InterpolatorType.LINEAR
    rotation_mode: RotationMode = RotationMode.SHORTEST
    preserve_turns: int = 0

    def __post_init__(self) -> None:
        if len(self.keyframes) < 2:
            raise ValueError("at least two keyframes are required")
        prev = -math.inf
        for k in self.keyframes:
            if not math.isfinite(k.time) or not math.isfinite(k.value):
                raise ValueError("keyframe values must be finite")
            if k.time < prev:
                raise ValueError("keyframes must be sorted")
            if k.time == prev:
                raise ValueError("keyframe times must be unique")
            prev = k.time
            if k.control_points is not None:
                x1, y1, x2, y2 = k.control_points
                if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
                    raise ValueError("Bezier controls must be finite")
                if not (0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0):
                    raise ValueError("Bezier x control points must lie in [0,1]")
        if not math.isfinite(self.preserve_turns):
            raise ValueError("preserve_turns must be finite")

    def _map_tau(self, tau: float) -> float:
        if not math.isfinite(tau):
            raise ValueError("tau must be finite")
        if self.loop_mode is LoopMode.LOOP:
            return tau % 1.0
        if self.loop_mode is LoopMode.PING_PONG:
            t = tau % 2.0
            return t if t <= 1.0 else 2.0 - t
        if self.loop_mode is LoopMode.HOLD:
            return max(0.0, min(1.0, tau))
        return max(0.0, min(1.0, tau))

    @staticmethod
    def _rotation_delta(a: float, b: float, mode: RotationMode, turns: int) -> float:
        raw = b - a
        if mode is RotationMode.PRESERVE_TURNS:
            return raw + 360.0 * turns
        if mode is RotationMode.FORWARD:
            d = raw % 360.0
            return d if d != 0.0 else 360.0
        return (raw + 180.0) % 360.0 - 180.0

    @staticmethod
    def _bezier_y(x: float, y1: float, y2: float) -> float:
        return 3*(1-x)**2*x*y1 + 3*(1-x)*x*x*y2 + x**3

    @staticmethod
    def _solve_bezier_x(target: float, x1: float, x2: float) -> float:
        def f(u: float) -> float:
            return 3*(1-u)**2*u*x1 + 3*(1-u)*u*u*x2 + u**3 - target
        def df(u: float) -> float:
            return 3*(1-u)**2*x1 + 6*(1-u)*u*(x2-x1) + 3*u*u*(1-x2)
        u = target
        for _ in range(8):
            d = df(u)
            if abs(d) < 1e-10:
                break
            nxt = u - f(u)/d
            if not 0.0 <= nxt <= 1.0:
                break
            if abs(nxt-u) <= 1e-7:
                return nxt
            u = nxt
        lo, hi = 0.0, 1.0
        for _ in range(32):
            u = (lo+hi)/2.0
            value = f(u)
            if abs(value) <= 1e-7:
                return u
            if value < 0:
                lo = u
            else:
                hi = u
        return (lo+hi)/2.0

    def evaluate(self, tau: float) -> float:
        tau = self._map_tau(tau)
        if tau <= self.keyframes[0].time:
            return self.keyframes[0].value
        if tau >= self.keyframes[-1].time:
            return self.keyframes[-1].value
        idx = next(i for i in range(len(self.keyframes)-1) if self.keyframes[i].time <= tau <= self.keyframes[i+1].time)
        a, b = self.keyframes[idx], self.keyframes[idx+1]
        u = (tau-a.time)/(b.time-a.time)
        delta = self._rotation_delta(a.value, b.value, self.rotation_mode, self.preserve_turns)
        if self.interpolator is InterpolatorType.HARMONIC:
            factor = 0.5 - 0.5*math.cos(2*math.pi*u)
        elif self.interpolator is InterpolatorType.CUBIC_BEZIER and a.control_points:
            x1,y1,x2,y2 = a.control_points
            factor = self._bezier_y(self._solve_bezier_x(u,x1,x2),y1,y2)
        else:
            factor = u
        value = a.value + factor * delta
        if self.rotation_mode is RotationMode.SHORTEST:
            return value % 360.0
        return value
