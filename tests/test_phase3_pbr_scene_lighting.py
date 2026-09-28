from __future__ import annotations

import numpy as np

from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane
from ai_gif_studio.temporal_engine.material_pbr import DirectLight, PBRMaterial
from ai_gif_studio.temporal_engine.motion import CameraMotionTrack, MotionKeyframe
from ai_gif_studio.temporal_engine.pbr_manuscript import render_pbr_manuscript
from ai_gif_studio.temporal_engine.pbr_motion import PBRMotionRenderer
from ai_gif_studio.temporal_engine.timeline import AnimationTimeline


def _scene() -> tuple[ManuscriptAsset, CameraState, ManuscriptPlane]:
    rgba = np.zeros((16, 16, 4), dtype=np.float32)
    rgba[3:13, 3:13, :3] = 1.0
    rgba[3:13, 3:13, 3] = 1.0
    asset = ManuscriptAsset(rgba)
    camera = CameraState(
        position=(0.0, 0.0, 10.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
    )
    plane = ManuscriptPlane(
        center=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        half_width=2.0,
        half_height=2.0,
    )
    return asset, camera, plane


def test_multi_light_scene_is_deterministic_and_accumulative() -> None:
    asset, camera, plane = _scene()
    material = PBRMaterial(albedo=(0.72, 0.48, 0.22), roughness=0.42, metallic=0.15)
    key = DirectLight(direction=(0.0, 0.0, 1.0), intensity=1.0)
    fill = DirectLight(direction=(1.0, 0.0, 1.0), color=(0.4, 0.6, 1.0), intensity=0.5)

    one = render_pbr_manuscript(
        asset, camera, plane, (32, 32), material=material, lights=(key,)
    )
    multi_a = render_pbr_manuscript(
        asset, camera, plane, (32, 32), material=material, lights=(key, fill)
    )
    multi_b = render_pbr_manuscript(
        asset, camera, plane, (32, 32), material=material, lights=(key, fill)
    )

    assert one.dtype == np.float32
    assert multi_a.dtype == np.float32
    assert np.array_equal(multi_a, multi_b)
    assert not np.array_equal(one, multi_a)
    assert np.all(multi_a[..., :3] >= one[..., :3] - 1e-7)


def test_legacy_single_light_path_matches_scene_contract() -> None:
    asset, camera, plane = _scene()
    material = PBRMaterial(albedo=(0.5, 0.5, 0.5), roughness=0.5, metallic=0.0)
    light = DirectLight(direction=(0.0, 0.0, 1.0), intensity=0.8)

    legacy = render_pbr_manuscript(
        asset,
        camera,
        plane,
        (32, 32),
        material.albedo,
        material.roughness,
        metallic=material.metallic,
        light=light.direction,
        light_color=light.color,
        light_intensity=light.intensity,
    )
    contract = render_pbr_manuscript(
        asset, camera, plane, (32, 32), material=material, lights=(light,)
    )

    assert np.array_equal(legacy, contract)


def test_motion_renderer_accepts_scene_contracts() -> None:
    asset, _, plane = _scene()
    timeline = AnimationTimeline(total_duration_sec=0.1, fps=10.0)
    motion = CameraMotionTrack(
        keyframes=(
            MotionKeyframe(0.0, (0.0, 0.0, 10.0), (0.0, 0.0, 0.0)),
            MotionKeyframe(0.1, (0.1, 0.0, 10.0), (0.0, 0.0, 0.0)),
        ),
        aspect=1.0,
    )
    renderer = PBRMotionRenderer(timeline, motion, (32, 32))
    frames, delays = renderer.render_sequence(
        asset,
        plane,
        albedo=(0.6, 0.4, 0.2),
        roughness=0.5,
        material=PBRMaterial(albedo=(0.6, 0.4, 0.2), roughness=0.5),
        lights=(
            DirectLight(direction=(0.0, 0.0, 1.0)),
            DirectLight(direction=(1.0, 0.0, 1.0), intensity=0.25),
        ),
    )

    assert len(frames) == timeline.total_frames
    assert len(delays) == timeline.total_frames
    assert all(frame.dtype == np.float32 for frame in frames)
    assert all(frame.shape == (32, 32, 4) for frame in frames)
