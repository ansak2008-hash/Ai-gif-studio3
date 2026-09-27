"""Temporal engine: deterministic timeline, curves, color, and GIF encoding.

Manuscript animation primitives are re-exported here temporarily;
they will move to `ai_gif_studio.manuscript` in Phase 5.
"""
from .timeline import AnimationTimeline, FrameTiming
from .curves import (
    Keyframe,
    MotionCurve,
    InterpolatorType,
    LoopMode,
    RotationMode,
)
from .color import linearize_srgb, encode_srgb
from .affine import AffineTransform, warp_premultiplied_rgba
from .glint import GlintParameters, gaussian_glint
from .palette import build_global_palette, quantize_frames_global
from .quality import validate_temporal_sequence

# --- Manuscript engine (Phase 1 + 2, temporary location) ---
from .camera import CameraState, CameraModel, project_points
from .manuscript_plane import (
    ManuscriptPlane,
    homography_from_corners,
    warp_manuscript,
)
from .bevel import BevelProfile
from .depth_field import DepthField

__all__ = [
    # Temporal
    "AnimationTimeline",
    "FrameTiming",
    "Keyframe",
    "MotionCurve",
    "InterpolatorType",
    "LoopMode",
    "RotationMode",
    "linearize_srgb",
    "encode_srgb",
    "AffineTransform",
    "warp_premultiplied_rgba",
    "GlintParameters",
    "gaussian_glint",
    "build_global_palette",
    "quantize_frames_global",
    "validate_temporal_sequence",
    # Manuscript (Phase 1 + 2)
    "CameraState",
    "CameraModel",
    "project_points",
    "ManuscriptPlane",
    "homography_from_corners",
    "warp_manuscript",
    "BevelProfile",
    "DepthField",
]
