import numpy as np
import pytest

from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane
from ai_gif_studio.temporal_engine.pbr_manuscript import render_pbr_manuscript

pytestmark = pytest.mark.unit


def _scene():
    rgba = np.ones((16, 16, 4), dtype=np.float32)
    rgba[..., :3] = 0.8
    asset = ManuscriptAsset(rgba, name="pbr-test")
    camera = CameraState(
        position=(0.0, 0.0, 4.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
    )
    plane = ManuscriptPlane(
        center=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        half_width=1.0,
        half_height=1.0,
    )
    return asset, camera, plane


def test_render_pbr_manuscript_produces_rgba():
    asset, camera, plane = _scene()
    result = render_pbr_manuscript(
        asset,
        camera,
        plane,
        (32, 32),
        albedo=[0.8, 0.3, 0.1],
        roughness=0.4,
        metallic=0.1,
    )

    assert result.shape == (32, 32, 4)
    assert result.dtype == np.float32
    assert np.isfinite(result).all()
    assert np.all(result >= 0.0)
    assert np.any(result[..., 3] > 0.0)
    assert np.any(result[..., :3] > 0.0)


def test_render_pbr_manuscript_is_deterministic():
    asset, camera, plane = _scene()
    kwargs = dict(
        albedo=[0.7, 0.4, 0.2],
        roughness=0.35,
        metallic=0.2,
        light=(0.2, 0.1, 1.0),
        light_color=[1.0, 0.9, 0.8],
        light_intensity=1.25,
    )
    first = render_pbr_manuscript(asset, camera, plane, (24, 24), **kwargs)
    second = render_pbr_manuscript(asset, camera, plane, (24, 24), **kwargs)
    np.testing.assert_array_equal(first, second)


def test_render_pbr_manuscript_rejects_plane_behind_camera():
    asset, camera, _ = _scene()
    plane = ManuscriptPlane(
        center=(0.0, 0.0, 6.0),
        normal=(0.0, 0.0, 1.0),
        half_width=1.0,
        half_height=1.0,
    )
    with pytest.raises(ValueError, match="near plane"):
        render_pbr_manuscript(
            asset,
            camera,
            plane,
            (16, 16),
            albedo=[0.8, 0.3, 0.1],
            roughness=0.4,
        )
