"""Deterministic temporal primitives plus an isolated manuscript animation engine."""

from .affine import AffineTransform, warp_premultiplied_rgba
from .bevel import BevelProfile
from .camera import CameraModel, CameraState, project_points
from .color import encode_srgb, linearize_srgb
from .curves import (
    InterpolatorType,
    Keyframe,
    LoopMode,
    MotionCurve,
    RotationMode,
)
from .depth_field import DepthField
from .glint import GlintParameters, gaussian_glint
from .manuscript_plane import ManuscriptPlane, homography_from_corners, warp_manuscript
from .palette import build_global_palette, quantize_frames_global
from .particles import ParticleField, render_particles
from .pbr_renderer import render_pbr_depth_field
from .pbr_surface import shade_depth_field, shade_depth_field_from_camera
from .quality import validate_temporal_sequence
from .timeline import AnimationTimeline, FrameTiming

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
    "ParticleField",
    "render_particles",
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
    "render_pbr_depth_field",
    "shade_depth_field",
    "shade_depth_field_from_camera",
]
