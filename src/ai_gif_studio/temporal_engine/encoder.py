from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .color_export import ExportColorSpec, linear_rgba_to_srgb_rgb
from .palette import build_global_palette, quantize_frames_global


def encode_gif(
    frames: list[np.ndarray], delays_cs: tuple[int, ...], output: Path | str
) -> str:
    if not frames:
        raise ValueError("frames cannot be empty")
    if len(frames) != len(delays_cs):
        raise ValueError("frame/delay count mismatch")
    shape = np.asarray(frames[0]).shape
    if len(shape) != 3 or shape[2] != 3 or any(
        np.asarray(frame).shape != shape for frame in frames
    ):
        raise ValueError("all frames must have a consistent HxWx3 RGB shape")
    if any(int(d) < 1 for d in delays_cs):
        raise ValueError("GIF delays must be >=1cs")
    palette = build_global_palette(frames, 256)
    indexed = quantize_frames_global(frames, palette)
    indexed[0].save(
        str(output),
        save_all=True,
        append_images=indexed[1:],
        duration=[int(d) * 10 for d in delays_cs],
        loop=0,
        disposal=2,
        optimize=False,
    )
    return hashlib.sha256(Path(output).read_bytes()).hexdigest()


def encode_linear_gif(
    frames_rgba_linear: list[np.ndarray],
    delays_cs: tuple[int, ...],
    output: Path | str,
    color_spec: ExportColorSpec | None = None,
) -> str:
    """Convert linear RGBA frames through the explicit color boundary and encode GIF."""
    if not frames_rgba_linear:
        raise ValueError("frames_rgba_linear cannot be empty")
    rgb_frames = [linear_rgba_to_srgb_rgb(frame, color_spec) for frame in frames_rgba_linear]
    return encode_gif(rgb_frames, delays_cs, output)
