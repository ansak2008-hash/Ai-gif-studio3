from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TemporalValidation:
    passed: bool
    max_mean_abs_diff: float
    median_mean_abs_diff: float
    spike_index: int | None


def validate_temporal_sequence(
    frames: list[np.ndarray], spike_factor: float = 4.0
) -> TemporalValidation:
    if len(frames) < 2:
        return TemporalValidation(True, 0.0, 0.0, None)
    diffs = [
        float(
            np.mean(
                np.abs(
                    frames[i].astype(np.float32) - frames[i - 1].astype(np.float32)
                )
            )
        )
        for i in range(1, len(frames))
    ]
    med = float(np.median(diffs))
    mx = max(diffs)
    idx = diffs.index(mx) + 1
    passed = med == 0.0 and mx == 0.0 or mx <= max(1.0, med * spike_factor + 8.0)
    return TemporalValidation(passed, mx, med, None if passed else idx)
