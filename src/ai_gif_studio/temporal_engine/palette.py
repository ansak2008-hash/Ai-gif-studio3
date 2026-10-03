from __future__ import annotations

import numpy as np
from PIL import Image


def build_global_palette(
    frames: list[np.ndarray], colors: int = 256, sample_pixels: int = 65536
) -> Image.Image:
    if not frames:
        raise ValueError("frames cannot be empty")
    if not 1 <= colors <= 256:
        raise ValueError("colors must be 1..256")
    rng = np.random.default_rng(0)
    per = max(1, sample_pixels // len(frames))
    chunks = []
    for frame in frames:
        flat = np.asarray(frame, dtype=np.uint8).reshape(-1, 3)
        if len(flat) > per:
            flat = flat[rng.choice(len(flat), per, replace=False)]
        chunks.append(flat)
    sample = np.concatenate(chunks, axis=0)
    side = max(1, int(np.ceil(np.sqrt(len(sample)))))
    tiled = np.zeros((side * side, 3), dtype=np.uint8)
    tiled[: len(sample)] = sample
    return Image.fromarray(tiled.reshape(side, side, 3), "RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )


def quantize_frames_global(
    frames: list[np.ndarray], palette: Image.Image
) -> list[Image.Image]:
    if palette.palette is None:
        raise ValueError("palette must contain an RGB color table")
    result = []
    for frame in frames:
        rgb = np.asarray(frame, dtype=np.uint8)
        image = Image.fromarray(rgb, "RGB")
        result.append(image.quantize(palette=palette, dither=Image.Dither.NONE))
    return result
