import numpy as np
import pytest
from PIL import Image

from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_pipeline import ManuscriptPipeline
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane
from ai_gif_studio.temporal_engine.motion import CameraMotionTrack, MotionKeyframe
from ai_gif_studio.temporal_engine.timeline import AnimationTimeline

pytestmark = pytest.mark.integration


def _pipeline() -> tuple[ManuscriptPipeline, ManuscriptAsset, ManuscriptPlane]:
    asset = ManuscriptAsset(np.full((8, 8, 4), 0.8, dtype=np.float32))
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
        viewport=(32, 32),
    )
    return pipeline, asset, plane


def test_final_pipeline_writes_deterministic_gif(tmp_path):
    pipeline, asset, plane = _pipeline()
    kwargs = dict(
        albedo=[0.8, 0.3, 0.1],
        roughness=0.4,
        metallic=0.1,
        light=(0.2, 0.1, 1.0),
        light_color=[1.0, 0.9, 0.8],
        light_intensity=1.0,
    )
    first = tmp_path / "first.gif"
    second = tmp_path / "second.gif"

    digest_first = pipeline.render_to_gif(asset, plane, first, **kwargs)
    digest_second = pipeline.render_to_gif(asset, plane, second, **kwargs)

    assert first.exists() and second.exists()
    assert digest_first == digest_second
    with Image.open(first) as image:
        assert image.format == "GIF"
        assert image.n_frames == 2
        assert image.size == (32, 32)


def test_final_pipeline_returns_temporal_quality_gate():
    pipeline, asset, plane = _pipeline()
    frames, delays, validation = pipeline.render_frames(
        asset,
        plane,
        albedo=[0.7, 0.4, 0.2],
        roughness=0.35,
        metallic=0.2,
    )
    assert len(frames) == 2
    assert len(delays) == 2
    assert validation.passed
    assert validation.spike_index is None
    assert all(frame.shape == (32, 32, 4) for frame in frames)
