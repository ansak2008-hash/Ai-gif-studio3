import numpy as np
import pytest

from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.depth_field import DepthField
from ai_gif_studio.temporal_engine.pbr_renderer import render_pbr_depth_field

pytestmark = pytest.mark.unit


def test_render_pbr_depth_field_returns_linear_rgba():
    field = DepthField(
        distance_px=np.array([[1.0, -1.0]], dtype=np.float32),
        height=np.array([[1.0, 0.0]], dtype=np.float32),
        normals=np.array(
            [[[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]],
            dtype=np.float32,
        ),
    )
    camera = CameraState(
        position=(0.0, 0.0, 4.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=2.0,
    )
    points = np.array(
        [[[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]]],
        dtype=np.float64,
    )

    result = render_pbr_depth_field(
        field,
        camera,
        points,
        [0.8, 0.3, 0.1],
        0.4,
    )

    assert result.shape == (1, 2, 4)
    assert result.dtype == np.float32
    assert np.isfinite(result).all()
    assert np.all(result[0, 0, :3] >= 0.0)
    np.testing.assert_array_equal(result[0, 0, 3], 1.0)
    np.testing.assert_array_equal(result[0, 1], np.zeros(4, dtype=np.float32))


def test_render_pbr_depth_field_is_deterministic():
    field = DepthField(
        distance_px=np.ones((2, 2), dtype=np.float32),
        height=np.ones((2, 2), dtype=np.float32),
        normals=np.broadcast_to(
            np.array([0.0, 0.0, 1.0], dtype=np.float32),
            (2, 2, 3),
        ).copy(),
    )
    camera = CameraState(
        position=(0.0, 0.0, 4.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
    )
    points = np.zeros((2, 2, 3), dtype=np.float64)
    kwargs = dict(
        albedo=[0.7, 0.4, 0.2],
        roughness=0.35,
        metallic=0.15,
        light=(0.2, 0.1, 1.0),
        light_color=[1.0, 0.9, 0.8],
        light_intensity=1.5,
    )
    first = render_pbr_depth_field(field, camera, points, **kwargs)
    second = render_pbr_depth_field(field, camera, points, **kwargs)
    np.testing.assert_array_equal(first, second)
