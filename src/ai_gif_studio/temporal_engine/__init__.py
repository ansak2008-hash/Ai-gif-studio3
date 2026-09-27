"""Deterministic temporal primitives plus an isolated manuscript animation engine."""
from .timeline import AnimationTimeline, FrameTiming
from .curves import Keyframe, MotionCurve, InterpolatorType, LoopMode, RotationMode
from .color import linearize_srgb, encode_srgb
from .affine import AffineTransform, warp_premultiplied_rgba
from .glint import GlintParameters, gaussian_glint
from .palette import build_global_palette, quantize_frames_global
from .quality import validate_temporal_sequence
from .manuscript import ManuscriptAsset, MaterialPreset, alpha_bounds
from .camera import CameraState, CameraModel, project_points
from .manuscript_plane import ManuscriptPlane, homography_from_corners, warp_manuscript
from .depth_field import DepthField
from .cinematic_camera import CameraKey, CinematicCamera
from .material import Material, MaterialSpec, material_preset, normals_from_alpha, shade_metallic
from .manuscript_renderer import ManuscriptCinematicProfile, ManuscriptCinematicRenderer
from .particles import ParticleField, render_particles
__all__=["AnimationTimeline","FrameTiming","Keyframe","MotionCurve","InterpolatorType","LoopMode","RotationMode",
"linearize_srgb","encode_srgb","AffineTransform","warp_premultiplied_rgba","GlintParameters","gaussian_glint",
"build_global_palette","quantize_frames_global","validate_temporal_sequence","ManuscriptAsset","MaterialPreset",
"alpha_bounds","CameraState","CameraModel","project_points","ManuscriptPlane","homography_from_corners","warp_manuscript","CameraKey","CinematicCamera","Material","MaterialSpec","material_preset","normals_from_alpha",
"shade_metallic","ManuscriptCinematicProfile","ManuscriptCinematicRenderer","ParticleField","render_particles"]