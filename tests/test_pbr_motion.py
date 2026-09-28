import numpy as np
import pytest

from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane
from ai_gif_studio.temporal_engine.motion import (
    CameraMotionTrack,
    MotionKeyframe,
    smoothstep01,
)
from ai_gif_studio.temporal_engine.pbr_motion import PBRMotionRenderer
from ai_gif_studio.temporal_engine.timeline import AnimationTimeline

pytestmark = pytest.mark.unit


def _track() -> CameraMotionTrack:
    return CameraMotionTrack(
        keyframes=(
            MotionKeyframe(0.0, (0.0, 0.0, 4.0), (0.0, 0.0, 0.0)),
            MotionKeyframe(1.0, (0.5, 0.0, 3.5), (0.0, 0.1, 0.0), roll_deg=20.0),
        ),
        aspect=1.0,
    )


def test_smoothstep_boundaries_and_midpoint():
    assert smoothstep01(0.0) == 0.0
    assert smoothstep01(1.0) == 1.0
    assert smoothstep01(0.5) == 0.5


def test_motion_track_interpolates_and_clamps():
    track = _track()
    assert track.sample(-1.0) == track.sample(0.0)
    assert track.sample(2.0) == track.sample(1.0)
    middle = track.sample(0.5)
    assert middle.position == (0.25, 0.0, 3.75)
    assert middle.target == (0.0, 0.05, 0.0)
    assert middle.roll_deg == 10.0


def test_motion_track_rejects_non_monotonic_keys():
    with pytest.raises(ValueError, match="strictly increasing"):
        CameraMotionTrack(
            keyframes=(
                MotionKeyframe(0.0, (0.0, 0.0, 4.0), (0.0, 0.0, 0.0)),
                MotionKeyframe(0.0, (0.0, 0.0, 3.0), (0.0, 0.0, 0.0)),
            )
        )


def test_motion_renderer_is_deterministic():
    asset = ManuscriptAsset(np.ones((8, 8, 4), dtype=np.float32))
    plane = ManuscriptPlane(
        center=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        half_width=1.0,
        half_height=1.0,
    )
    renderer = PBRMotionRenderer(
        timeline=AnimationTimeline(1.0, 4.0, loop=False),
        motion=_track(),
        viewport=(20, 20),
    )
    kwargs = dict(
        albedo=[0.7, 0.4, 0.2],
        roughness=0.35,
        metallic=0.2,
        light=(0.2, 0.1, 1.0),
        light_color=[1.0, 0.9, 0.8],
        light_intensity=1.25,
    )
    first, delays_first = renderer.render_sequence(asset, plane, **kwargs)
    second, delays_second = renderer.render_sequence(asset, plane, **kwargs)

    assert len(first) == 4
    assert delays_first == delays_second
    assert all(frame.shape == (20, 20, 4) for frame in first)
    assert all(frame.dtype == np.float32 for frame in first)
    for a, b in zip(first, second):
        np.testing.assert_array_equal(a, b)


def test_motion_renderer_does_not_mutate_camera_contract():
    state = CameraState(
        position=(0.0, 0.0, 4.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
    )
    sampled = _track().sample(0.0)
    assert sampled.fov_y_deg == state.fov_y_deg
    assert sampled.aspect == state.aspect
