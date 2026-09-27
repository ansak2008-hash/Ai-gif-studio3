from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class FrameTiming:
    index: int
    timestamp_sec: float
    duration_sec: float
    delay_cs: int

@dataclass(frozen=True)
class AnimationTimeline:
    total_duration_sec: float
    fps: float
    loop: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.total_duration_sec) or self.total_duration_sec <= 0:
            raise ValueError("total_duration_sec must be finite and > 0")
        if not math.isfinite(self.fps) or self.fps <= 0:
            raise ValueError("fps must be finite and > 0")

    @property
    def total_frames(self) -> int:
        return max(1, int(round(self.total_duration_sec * self.fps)))

    @property
    def frame_times(self) -> tuple[float, ...]:
        n = self.total_frames
        return tuple(i * self.total_duration_sec / n for i in range(n))

    def progress(self, t: float) -> float:
        if not math.isfinite(t):
            raise ValueError("time must be finite")
        if self.loop:
            return (t % self.total_duration_sec) / self.total_duration_sec
        return max(0.0, min(1.0, t / self.total_duration_sec))

    def centisecond_delays(self) -> tuple[int, ...]:
        total_cs = int(round(self.total_duration_sec * 100.0))
        n = self.total_frames
        if total_cs < n:
            raise ValueError("GIF duration is too short to allocate >=1cs to every frame")
        delays = tuple(
            round((i + 1) * total_cs / n) - round(i * total_cs / n)
            for i in range(n)
        )
        if any(d < 1 for d in delays) or sum(delays) != total_cs:
            raise AssertionError("invalid centisecond allocation")
        return delays

    def timings(self) -> tuple[FrameTiming, ...]:
        times = self.frame_times
        delays = self.centisecond_delays()
        return tuple(FrameTiming(i, t, d / 100.0, delays[i]) for i, (t, d) in enumerate(zip(times, delays)))
