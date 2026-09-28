from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class CropMode(StrEnum):
    CENTER = "center"
    FIT = "fit"
    FILL = "fill"


class BlendMode(StrEnum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    ADD = "add"


@dataclass(frozen=True, slots=True)
class CropSpec:
    width: int
    height: int
    mode: CropMode = CropMode.FILL
    focus_x: float = 0.5
    focus_y: float = 0.5

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("crop dimensions must be positive")
        if not 0.0 <= self.focus_x <= 1.0 or not 0.0 <= self.focus_y <= 1.0:
            raise ValueError("crop focus must be between 0 and 1")


def crop_frame(frame: np.ndarray, spec: CropSpec) -> np.ndarray:
    """Deterministically crop/fill/fit a frame while preserving its channel count."""
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] not in (3, 4):
        raise ValueError("frame must have shape HxWx3 or HxWx4")
    if frame.dtype != np.uint8:
        raise ValueError("frame must use uint8 pixels")
    height, width = frame.shape[:2]
    target_ratio = spec.width / spec.height
    source_ratio = width / height

    if spec.mode is CropMode.FILL:
        if source_ratio > target_ratio:
            crop_h = height
            crop_w = max(1, round(height * target_ratio))
        else:
            crop_w = width
            crop_h = max(1, round(width / target_ratio))
        x = round(spec.focus_x * (width - crop_w))
        y = round(spec.focus_y * (height - crop_h))
        return frame[y:y + crop_h, x:x + crop_w].copy()

    if spec.mode is CropMode.CENTER:
        crop_w = min(width, spec.width)
        crop_h = min(height, spec.height)
        x = round(spec.focus_x * (width - crop_w))
        y = round(spec.focus_y * (height - crop_h))
        cropped = frame[y:y + crop_h, x:x + crop_w]
        return cv2.resize(cropped, (spec.width, spec.height), interpolation=cv2.INTER_AREA)

    scale = min(spec.width / width, spec.height / height)
    resized = cv2.resize(
        frame,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
    )
    output = np.zeros((spec.height, spec.width, frame.shape[2]), dtype=np.uint8)
    y = (spec.height - resized.shape[0]) // 2
    x = (spec.width - resized.shape[1]) // 2
    output[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
    if frame.shape[2] == 4:
        output[:, :, 3] = 0
        output[y:y + resized.shape[0], x:x + resized.shape[1], 3] = resized[:, :, 3]
    return output


def affine_transform(frame: np.ndarray, matrix: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Apply a validated 2x3 affine transform to an RGB/RGBA frame."""
    if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
        raise ValueError("affine matrix must be finite with shape 2x3")
    width, height = size
    if width < 1 or height < 1:
        raise ValueError("output dimensions must be positive")
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] not in (3, 4):
        raise ValueError("frame must be uint8 RGB/RGBA")
    return cv2.warpAffine(
        frame,
        np.asarray(matrix, dtype=np.float64),
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def perspective_transform(
    frame: np.ndarray,
    source_points: np.ndarray,
    destination_points: np.ndarray,
    size: tuple[int, int],
) -> np.ndarray:
    """Apply a deterministic four-point perspective warp."""
    src = np.asarray(source_points, dtype=np.float64)
    dst = np.asarray(destination_points, dtype=np.float64)
    if src.shape != (4, 2) or dst.shape != (4, 2):
        raise ValueError("perspective points must have shape 4x2")
    if not np.isfinite(src).all() or not np.isfinite(dst).all():
        raise ValueError("perspective points must be finite")
    if np.linalg.matrix_rank(cv2.getPerspectiveTransform(src.astype(np.float32), dst.astype(np.float32))) < 3:
        raise ValueError("perspective points are degenerate")
    width, height = size
    if width < 1 or height < 1:
        raise ValueError("output dimensions must be positive")
    return cv2.warpPerspective(
        frame,
        cv2.getPerspectiveTransform(src.astype(np.float32), dst.astype(np.float32)),
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def _validate_mask(mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    if mask.shape != shape or mask.dtype != np.uint8:
        raise ValueError("mask must match frame height/width and use uint8")
    return mask.astype(np.float32) / 255.0


def blend_frames(base: np.ndarray, overlay: np.ndarray, mask: np.ndarray | None = None, mode: BlendMode = BlendMode.NORMAL) -> np.ndarray:
    """Blend two equally sized RGB/RGBA frames using a bounded mask."""
    if base.shape != overlay.shape or base.ndim != 3 or base.shape[2] not in (3, 4):
        raise ValueError("base and overlay must have identical RGB/RGBA shape")
    if base.dtype != np.uint8 or overlay.dtype != np.uint8:
        raise ValueError("frames must use uint8 pixels")
    h, w = base.shape[:2]
    alpha = _validate_mask(mask, (h, w)) if mask is not None else np.ones((h, w), dtype=np.float32)
    channels = 3
    a = base[:, :, :channels].astype(np.float32) / 255.0
    b = overlay[:, :, :channels].astype(np.float32) / 255.0
    if mode is BlendMode.MULTIPLY:
        mixed = a * b
    elif mode is BlendMode.SCREEN:
        mixed = 1.0 - (1.0 - a) * (1.0 - b)
    elif mode is BlendMode.ADD:
        mixed = np.clip(a + b, 0.0, 1.0)
    else:
        mixed = b
    rgb = np.clip((a * (1.0 - alpha[:, :, None]) + mixed * alpha[:, :, None]) * 255.0, 0, 255).astype(np.uint8)
    if base.shape[2] == 4:
        base_alpha = base[:, :, 3].astype(np.float32) / 255.0
        overlay_alpha = overlay[:, :, 3].astype(np.float32) / 255.0
        out_alpha = overlay_alpha * alpha + base_alpha * (1.0 - overlay_alpha * alpha)
        return np.dstack((rgb, np.round(out_alpha * 255.0).astype(np.uint8)))
    return rgb
