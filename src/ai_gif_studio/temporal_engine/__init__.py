"""Deterministic temporal primitives plus an isolated manuscript animation engine."""

from .affine import AffineTransform, warp_premultiplied_rgba
from .bevel import BevelProfile
from .blend import BlendMode, BlendModeEffect
from .camera import CameraModel, CameraState, project_points
from .color import encode_srgb, linearize_srgb
from .color_effects import ColorMatrixEffect, ExposureEffect, GammaEffect, RGBGainEffect
from .color_export import ExportColorSpec, linear_rgba_to_srgb_rgb, tone_map_reinhard
from .compositor import BlendLayer, composite_blend_layers, composite_layers, composite_over
from .curves import (
    InterpolatorType,
    Keyframe,
    LoopMode,
    MotionCurve,
    RotationMode,
)
from .depth_field import DepthField
from .effect_stack import EffectStack
from .framing import FramingEffect, FramingMode, FramingSpec
from .geometry_transforms import (
    AffineTransformEffect,
    AffineTransformSpec,
    PerspectiveTransformEffect,
    PerspectiveTransformSpec,
)
from .glint import GlintParameters, gaussian_glint
from .keyframed_transforms import AffineTransformKeyframe, AffineTransformTrack
from .manuscript_pipeline import ManuscriptPipeline
from .manuscript_plane import ManuscriptPlane, homography_from_corners, warp_manuscript
from .material_pbr import DirectLight, PBRMaterial, shade_pbr_lights
from .motion import CameraMotionTrack, MotionKeyframe, smoothstep01
from .motion_layer import MotionLayer
from .palette import build_global_palette, quantize_frames_global
from .particles import ParticleField, render_particles
from .pbr_manuscript import render_pbr_manuscript
from .pbr_motion import PBRMotionRenderer
from .pbr_renderer import render_pbr_depth_field
from .pbr_surface import shade_depth_field, shade_depth_field_from_camera
from .quality import validate_temporal_sequence
from .render_buffer import RenderBuffer
from .render_graph import RenderGraph, RenderNode
from .render_mask import RenderMask
from .selective_region import SelectiveRegionEffect
from .temporal_compositor import composite_motion_layers
from .temporal_effects import TemporalFadeEffect
from .temporal_stack import TemporalEffect, TemporalEffectStack
from .temporal_transitions import TemporalCrossfadeEffect
from .timeline import AnimationTimeline, FrameTiming
from .tone_curve import ToneCurve, ToneCurveEffect

__all__ = [
    # Temporal
    "AnimationTimeline",
    "FrameTiming",
    "linear_rgba_to_srgb_rgb",
    "tone_map_reinhard",
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
    "RenderBuffer",
    "RenderMask",
    "RenderNode",
    "RenderGraph",
    "SelectiveRegionEffect",
    "EffectStack",
    "FramingMode",
    "FramingSpec",
    "FramingEffect",
    "AffineTransformSpec",
    "AffineTransformEffect",
    "PerspectiveTransformSpec",
    "PerspectiveTransformEffect",
    "AffineTransformKeyframe",
    "AffineTransformTrack",
    "MotionLayer",
    "TemporalFadeEffect",
    "TemporalEffect",
    "TemporalEffectStack",
    "TemporalCrossfadeEffect",
    "composite_motion_layers",
    "ExposureEffect",
    "GammaEffect",
    "RGBGainEffect",
    "ColorMatrixEffect",
    "ToneCurve",
    "ToneCurveEffect",
    "BlendMode",
    "BlendModeEffect",
    "BlendLayer",
    "composite_over",
    "composite_layers",
    "composite_blend_layers",
    "apply_transform_state",
    # Manuscript (Phase 1 + 2)
    "CameraState",
    "CameraModel",
    "ExportColorSpec",
    "project_points",
    "ManuscriptPipeline",
    "ManuscriptPlane",
    "homography_from_corners",
    "warp_manuscript",
    "BevelProfile",
    "DepthField",
    "CameraMotionTrack",
    "MotionKeyframe",
    "PBRMotionRenderer",
    "render_pbr_manuscript",
    "smoothstep01",
    "render_pbr_depth_field",
    "PBRMaterial",
    "DirectLight",
    "shade_pbr_lights",
    "shade_depth_field",
    "shade_depth_field_from_camera",
]

from .transform_binding import apply_transform_state
