import numpy as np
import pytest

from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.depth_field import DepthField
from ai_gif_studio.temporal_engine.pbr_surface import (
    shade_depth_field,
    shade_depth_field_from_camera,
)

pytestmark = pytest.mark.unit


def test_shade_depth_field_uses_stored_normals_and_masks_outside():
    distance = np.array([[1.0, -1.0]], dtype=np.float32)
    height = np.array([[1.0, 0.0]], dtype=np.float32)
    normals = np.array(
        [[[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]],
        dtype=np.float32,
    )
    field = DepthField(distance_px=distance, height=height, normals=normals)

    result = shade_depth_field(
        field,
        view=np.array([0.0, 0.0, 1.0]),
        light=np.array([0.0, 0.0, 1.0]),
        albedo=[0.8, 0.3, 0.1],
        roughness=0.4,
    )

    assert result.shape == (1, 2, 3)
    assert result.dtype == np.float64
    assert np.isfinite(result).all()
    assert np.all(result[0, 0] > 0.0)
    np.testing.assert_array_equal(result[0, 1], np.zeros(3, dtype=np.float64))


def test_shade_depth_field_consumes_canonical_normals_without_recomputing():
    distance = np.ones((1, 1), dtype=np.float32)
    height = np.ones((1, 1), dtype=np.float32)
    tilted = np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32)
    field = DepthField(distance_px=distance, height=height, normals=tilted)

    result = shade_depth_field(
        field,
        view=np.array([0.0, 0.0, 1.0]),
        light=np.array([0.0, 0.0, 1.0]),
        albedo=[0.8, 0.3, 0.1],
        roughness=0.4,
    )

    np.testing.assert_array_equal(result, np.zeros((1, 1, 3), dtype=np.float64))


def test_shade_depth_field_is_deterministic():
    field = DepthField.from_alpha(
        np.pad(
            np.ones((8, 8), dtype=np.float32),
            4,
        ),
        bevel_width_px=4.0,
    )
    kwargs = dict(
        view=np.array([0.0, 0.0, 1.0]),
        light=np.array([0.2, 0.1, 1.0]),
        albedo=[0.7, 0.4, 0.2],
        roughness=0.35,
        metallic=0.15,
        light_color=[1.0, 0.9, 0.8],
        light_intensity=1.5,
    )
    first = shade_depth_field(field, **kwargs)
    second = shade_depth_field(field, **kwargs)
    np.testing.assert_array_equal(first, second)


def test_shade_depth_field_rejects_invalid_field_shape():
    distance = np.zeros((4, 4), dtype=np.float32)
    height = np.zeros((4, 4), dtype=np.float32)
    normals = np.zeros((4, 4, 2), dtype=np.float32)
    field = DepthField(distance_px=distance, height=height, normals=normals)

    with pytest.raises(ValueError, match="normals"):
        shade_depth_field(
            field,
            view=np.array([0.0, 0.0, 1.0]),
            light=np.array([0.0, 0.0, 1.0]),
            albedo=[0.8, 0.3, 0.1],
            roughness=0.4,
        )


def test_shade_depth_field_from_camera_matches_explicit_view_vectors():
    field = DepthField(
        distance_px=np.ones((1, 2), dtype=np.float32),
        height=np.ones((1, 2), dtype=np.float32),
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
        aspect=1.0,
    )
    points = np.array(
        [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]],
        dtype=np.float64,
    )
    explicit_view = camera.position - points

    expected = shade_depth_field(
        field,
        explicit_view,
        np.array([0.0, 1.0, 0.0]),
        [0.8, 0.3, 0.1],
        0.4,
    )
    actual = shade_depth_field_from_camera(
        field,
        camera,
        points,
        [0.8, 0.3, 0.1],
        0.4,
    )
    np.testing.assert_array_equal(actual, expected)
    assert np.isfinite(actual).all()


def test_shade_depth_field_from_camera_rejects_point_shape():
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
    with pytest.raises(ValueError, match="surface_points_world"):
        shade_depth_field_from_camera(
            field,
            camera,
            np.zeros((2, 2, 2), dtype=np.float64),
            [0.8, 0.3, 0.1],
            0.4,
        )


def test_camera_path_transforms_image_normal_into_world_space():
    field = DepthField(
        distance_px=np.ones((1, 1), dtype=np.float32),
        height=np.ones((1, 1), dtype=np.float32),
        normals=np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32),
    )
    camera = CameraState(
        position=(0.0, 0.0, 4.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
        roll_deg=90.0,
    )
    points = np.zeros((1, 1, 3), dtype=np.float64)
    result = shade_depth_field_from_camera(
        field,
        camera,
        points,
        [0.8, 0.3, 0.1],
        0.4,
    )
    expected = shade_depth_field(
        field,
        np.array([[[0.0, 0.0, 4.0]]]),
        np.array([0.0, 0.0, 1.0]),
        [0.8, 0.3, 0.1],
        0.4,
    )
    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=1e-12)
