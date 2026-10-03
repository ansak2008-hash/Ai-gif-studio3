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
    sampled = tiled[: len(sample)].reshape(-1, 3)
    unique = np.unique(sampled, axis=0)
    if len(unique) <= colors:
        exact = Image.fromarray(unique.reshape(1, len(unique), 3), "RGB")
        return exact.quantize(
            colors=len(unique), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
    return Image.fromarray(tiled.reshape(side, side, 3), "RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )


def quantize_frames_global(
    frames: list[np.ndarray], palette: Image.Image
) -> list[Image.Image]:
    if palette.palette is None:
        raise ValueError("palette must contain an RGB color table")
    colors = sorted(palette.palette.colors.items(), key=lambda item: item[1])
    if not colors:
        raise ValueError("palette must contain an RGB color table")
    pal = np.asarray([color for color, _index in colors], dtype=np.int16)
    result = []
    for frame in frames:
        rgb = np.asarray(frame, dtype=np.uint8)
        flat = rgb.reshape(-1, 3).astype(np.int16)
        idx = np.empty(len(flat), np.uint8)
        for start in range(0, len(flat), 16384):
            block = flat[start : start + 16384]
            dist = ((block[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
            idx[start : start + len(block)] = np.argmin(dist, axis=1).astype(np.uint8)
        out = Image.fromarray(idx.reshape(rgb.shape[:2]), "P")
        out.putpalette(palette.getpalette())
        result.append(out)
    return result
