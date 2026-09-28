from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

import cv2
import numpy as np


class TransformOp(StrEnum):
    RESIZE = "resize"
    ROTATE_90 = "rotate_90"
    FLIP_H = "flip_h"
    FLIP_V = "flip_v"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    BLUR = "blur"
    SHARPEN = "sharpen"
    VIGNETTE = "vignette"
    POSTERIZE = "posterize"
    PIXELATE = "pixelate"


@dataclass(frozen=True, slots=True)
class TransformStep:
    op: TransformOp
    value: float | int | tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class TransformSpec:
    steps: tuple[TransformStep, ...] = ()

    def __post_init__(self) -> None:
        if len(self.steps) > 32:
            raise ValueError("a TransformSpec may contain at most 32 steps")


def _validate_frame(frame: np.ndarray) -> np.ndarray:
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a numpy array")
    if frame.ndim not in {3} or frame.shape[2] not in {3, 4}:
        raise ValueError("frame must have shape HxWx3 or HxWx4")
    if frame.dtype != np.uint8:
        raise ValueError("frame must use uint8 pixels")
    if frame.shape[0] < 1 or frame.shape[1] < 1:
        raise ValueError("frame dimensions must be positive")
    return frame


def _odd_kernel(value: float | int | None, default: int = 3, maximum: int = 31) -> int:
    size = default if value is None else int(round(float(value)))
    size = max(1, min(maximum, size))
    return size if size % 2 else size + 1


def _resize(frame: np.ndarray, value: float | int | tuple[int, int] | None) -> np.ndarray:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("resize tuple must be (width, height)")
        width, height = int(value[0]), int(value[1])
        if width < 1 or height < 1:
            raise ValueError("resize dimensions must be positive")
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    scale = 1.0 if value is None else float(value)
    if not 0.01 <= scale <= 8.0:
        raise ValueError("resize scale must be between 0.01 and 8")
    height, width = frame.shape[:2]
    target = (max(1, round(width * scale)), max(1, round(height * scale)))
    return cv2.resize(frame, target, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)


def _adjust_hsv(frame: np.ndarray, saturation: float) -> np.ndarray:
    rgb = frame[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    if frame.shape[2] == 4:
        return np.dstack((result, frame[:, :, 3]))
    return result


def _brightness_contrast(frame: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
    rgb = frame[:, :, :3].astype(np.float32)
    result = np.clip((rgb - 127.5) * contrast + 127.5 + brightness, 0, 255).astype(np.uint8)
    if frame.shape[2] == 4:
        return np.dstack((result, frame[:, :, 3]))
    return result


def _sepia(frame: np.ndarray) -> np.ndarray:
    rgb = frame[:, :, :3].astype(np.float32)
    matrix = np.array(
        [[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]],
        dtype=np.float32,
    )
    result = np.clip(rgb @ matrix.T, 0, 255).astype(np.uint8)
    if frame.shape[2] == 4:
        return np.dstack((result, frame[:, :, 3]))
    return result


def _vignette(frame: np.ndarray, strength: float) -> np.ndarray:
    strength = float(strength)
    if not 0.0 <= strength <= 1.0:
        raise ValueError("vignette strength must be between 0 and 1")
    height, width = frame.shape[:2]
    y, x = np.ogrid[:height, :width]
    dx = (x - (width - 1) / 2) / max(1.0, width / 2)
    dy = (y - (height - 1) / 2) / max(1.0, height / 2)
    radius = np.sqrt(dx * dx + dy * dy)
    mask = np.clip(1.0 - strength * np.maximum(radius - 0.25, 0.0) / 0.75, 0.0, 1.0)
    result = np.clip(frame[:, :, :3].astype(np.float32) * mask[:, :, None], 0, 255).astype(np.uint8)
    if frame.shape[2] == 4:
        return np.dstack((result, frame[:, :, 3]))
    return result


def _posterize(frame: np.ndarray, levels: float | int | None) -> np.ndarray:
    count = 4 if levels is None else int(levels)
    if not 2 <= count <= 32:
        raise ValueError("posterize levels must be between 2 and 32")
    step = 255.0 / (count - 1)
    rgb = np.round(frame[:, :, :3].astype(np.float32) / step) * step
    result = np.clip(rgb, 0, 255).astype(np.uint8)
    if frame.shape[2] == 4:
        return np.dstack((result, frame[:, :, 3]))
    return result


def _pixelate(frame: np.ndarray, block_size: float | int | None) -> np.ndarray:
    block = 8 if block_size is None else int(block_size)
    if not 2 <= block <= 128:
        raise ValueError("pixelate block size must be between 2 and 128")
    height, width = frame.shape[:2]
    small = cv2.resize(
        frame,
        (max(1, width // block), max(1, height // block)),
        interpolation=cv2.INTER_AREA,
    )
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)


def apply_transform(frame: np.ndarray, spec: TransformSpec) -> np.ndarray:
    """Apply a bounded deterministic transform chain to one RGB/RGBA uint8 frame."""
    current = _validate_frame(frame).copy()
    for step in spec.steps:
        value = step.value
        if step.op is TransformOp.RESIZE:
            current = _resize(current, value)
        elif step.op is TransformOp.ROTATE_90:
            turns = 1 if value is None else int(value)
            current = np.rot90(current, turns % 4).copy()
        elif step.op is TransformOp.FLIP_H:
            current = cv2.flip(current, 1)
        elif step.op is TransformOp.FLIP_V:
            current = cv2.flip(current, 0)
        elif step.op is TransformOp.BRIGHTNESS:
            current = _brightness_contrast(current, 0.0 if value is None else float(value), 1.0)
        elif step.op is TransformOp.CONTRAST:
            contrast = 1.0 if value is None else float(value)
            if not 0.0 <= contrast <= 4.0:
                raise ValueError("contrast must be between 0 and 4")
            current = _brightness_contrast(current, 0.0, contrast)
        elif step.op is TransformOp.SATURATION:
            saturation = 1.0 if value is None else float(value)
            if not 0.0 <= saturation <= 4.0:
                raise ValueError("saturation must be between 0 and 4")
            current = _adjust_hsv(current, saturation)
        elif step.op is TransformOp.GRAYSCALE:
            gray = cv2.cvtColor(current[:, :, :3], cv2.COLOR_RGB2GRAY)
            result = np.repeat(gray[:, :, None], 3, axis=2)
            current = np.dstack((result, current[:, :, 3])) if current.shape[2] == 4 else result
        elif step.op is TransformOp.SEPIA:
            current = _sepia(current)
        elif step.op is TransformOp.BLUR:
            kernel = _odd_kernel(value)
            current = cv2.GaussianBlur(current, (kernel, kernel), 0)
        elif step.op is TransformOp.SHARPEN:
            amount = 1.0 if value is None else float(value)
            if not 0.0 <= amount <= 3.0:
                raise ValueError("sharpen amount must be between 0 and 3")
            blurred = cv2.GaussianBlur(current, (0, 0), 1.0)
            current = cv2.addWeighted(current, 1.0 + amount, blurred, -amount, 0)
        elif step.op is TransformOp.VIGNETTE:
            current = _vignette(current, 0.5 if value is None else float(value))
        elif step.op is TransformOp.POSTERIZE:
            current = _posterize(current, value)
        elif step.op is TransformOp.PIXELATE:
            current = _pixelate(current, value)
        else:
            raise ValueError(f"unsupported transform operation: {step.op}")
    return current


def apply_transform_batch(frames: Sequence[np.ndarray], spec: TransformSpec) -> list[np.ndarray]:
    """Apply one immutable transform specification to every frame in order."""
    return [apply_transform(frame, spec) for frame in frames]
