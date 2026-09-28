from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane
from ai_gif_studio.temporal_engine.manuscript_pipeline import ManuscriptPipeline
from ai_gif_studio.temporal_engine.material_pbr import DirectLight, PBRMaterial
from ai_gif_studio.temporal_engine.motion import CameraMotionTrack, MotionKeyframe
from ai_gif_studio.temporal_engine.timeline import AnimationTimeline

pytestmark = pytest.mark.integration


def _pipeline() -> tuple[ManuscriptPipeline, ManuscriptAsset, ManuscriptPlane]:
    rgba = np.zeros((8, 8, 4), dtype=np.float32)
    rgba[2:6, 2:6, :3] = 0.8
    rgba[2:6, 2:6, 3] = 1.0
    asset = ManuscriptAsset(rgba)
    plane = ManuscriptPlane(
        center=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        half_width=1.0,
        half_height=1.0,
    )
    motion = CameraMotionTrack(
        keyframes=(
            MotionKeyframe(0.0, (0.0, 0.0, 4.0), (0.0, 0.0, 0.0)),
            MotionKeyframe(1.0, (0.2, 0.0, 3.8), (0.0, 0.0, 0.0)),
        ),
        aspect=1.0,
    )
    pipeline = ManuscriptPipeline(
        timeline=AnimationTimeline(1.0, 2.0, loop=False),
        motion=motion,
        viewport=(24, 24),
    )
    return pipeline, asset, plane


def _scene_contract() -> tuple[PBRMaterial, tuple[DirectLight, ...]]:
    material = PBRMaterial(
        albedo=(0.72, 0.48, 0.22),
        roughness=0.42,
        metallic=0.15,
    )
    lights = (
        DirectLight((0.0, 0.0, 1.0), (1.0, 0.9, 0.8), 1.0),
        DirectLight((0.3, 0.1, 1.0), (0.4, 0.7, 1.0), 0.5),
    )
    return material, lights


def test_full_pipeline_propagates_material_and_multi_light_contract():
    pipeline, asset, plane = _pipeline()
    material, lights = _scene_contract()

    frames, delays, validation = pipeline.render_frames(
        asset,
        plane,
        albedo=material.albedo,
        roughness=material.roughness,
        metallic=material.metallic,
        material=material,
        lights=lights,
    )

    assert validation.passed
    assert len(frames) == pipeline.timeline.total_frames
    assert len(delays) == pipeline.timeline.total_frames
    assert all(frame.shape == (24, 24, 4) for frame in frames)
    assert all(frame.dtype == np.float32 for frame in frames)
    assert all(np.isfinite(frame).all() for frame in frames)


def test_full_pipeline_multi_light_gif_is_byte_deterministic(tmp_path):
    pipeline, asset, plane = _pipeline()
    material, lights = _scene_contract()

    first = tmp_path / "multi-light-first.gif"
    second = tmp_path / "multi-light-second.gif"

    kwargs = dict(
        albedo=material.albedo,
        roughness=material.roughness,
        metallic=material.metallic,
        material=material,
        lights=lights,
    )
    digest_first = pipeline.render_to_gif(asset, plane, first, **kwargs)
    digest_second = pipeline.render_to_gif(asset, plane, second, **kwargs)

    assert digest_first == digest_second
    assert first.read_bytes() == second.read_bytes()

    with Image.open(first) as image:
        assert image.format == "GIF"
        assert image.n_frames == pipeline.timeline.total_frames
        assert image.size == (24, 24)
