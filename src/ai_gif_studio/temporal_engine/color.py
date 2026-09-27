from __future__ import annotations

import numpy as np


def linearize_srgb(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb)
    if np.issubdtype(arr.dtype, np.integer):
        x = arr.astype(np.float32) / 255.0
    else:
        x = arr.astype(np.float32)
        if float(np.max(x, initial=0.0)) > 1.0:
            x = x / 255.0
    return np.where(
        x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4
    ).astype(np.float32)


def encode_srgb(linear: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(linear, dtype=np.float32), 0, 1)
    return (
        np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
        * 255.0
        + 0.5
    ).astype(np.uint8)
