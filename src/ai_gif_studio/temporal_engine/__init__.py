"""Deterministic temporal video/motion rendering primitives for the 320x320 studio contract."""

from .timeline import AnimationTimeline, FrameTiming
from .curves import Keyframe, MotionCurve, InterpolatorType, LoopMode, RotationMode
from .color import linearize_srgb, encode_srgb
from .affine import AffineTransform, warp_premultiplied_rgba
from .glint import GlintParameters, gaussian_glint
from .palette import build_global_palette, quantize_frames_global
from .quality import validate_temporal_sequence

__all__ = [
    "AnimationTimeline", "FrameTiming", "Keyframe", "MotionCurve",
    "InterpolatorType", "LoopMode", "RotationMode", "linearize_srgb",
    "encode_srgb", "AffineTransform", "warp_premultiplied_rgba",
    "GlintParameters", "gaussian_glint", "build_global_palette",
    "quantize_frames_global", "validate_temporal_sequence",
]
