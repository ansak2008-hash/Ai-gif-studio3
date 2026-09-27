import numpy as np
import pytest

from ai_gif_studio.temporal_engine.depth_field import DepthField


def square_alpha(size=64, start=16, end=48):
    a = np.zeros((size, size), dtype=np.float32)
    a[start:end, start:end] = 1.0
    return a


def test_depth_field_is_deterministic():
    a = square_alpha()
    x = DepthField.from_alpha(a)
    y = DepthField.from_alpha(a)
    np.testing.assert_array_equal(x.distance_px, y.distance_px)
    np.testing.assert_array_equal(x.height, y.height)
    np.testing.assert_array_equal(x.normals, y.normals)


def test_height_is_zero_outside_and_positive_inside():
    d = DepthField.from_alpha(square_alpha(32, 8, 24), bevel_width_px=6)
    assert np.all(d.height[0] == 0)
    assert float(d.height[16, 16]) > 0.9


def test_normals_are_unit_length():
    n = DepthField.from_alpha(square_alpha(32, 8, 24)).normals
    lengths = np.linalg.norm(n, axis=-1)
    assert np.allclose(lengths, 1.0, atol=1e-5)


def test_height_is_monotone_from_edge_to_center():
    d = DepthField.from_alpha(square_alpha(), bevel_width_px=8)
    values = [float(d.height[32, x]) for x in range(16, 32)]
    assert all(b >= a for a, b in zip(values, values[1:]))


def test_normals_point_inward_at_edges():
    d = DepthField.from_alpha(square_alpha(), bevel_width_px=6)
    n_left = d.normals[32, 17]
    assert n_left[0] > 0, f"Left-edge normal must have +x component: {n_left}"

    n_top = d.normals[17, 32]
    assert n_top[1] > 0, f"Top-edge normal must have +y component: {n_top}"


def test_bevel_width_changes_profile():
    a = square_alpha()
    narrow = DepthField.from_alpha(a, bevel_width_px=2)
    wide = DepthField.from_alpha(a, bevel_width_px=16)
    assert not np.array_equal(narrow.height, wide.height)


def test_normals_at_center_are_flat():
    n = DepthField.from_alpha(square_alpha(), bevel_width_px=8).normals[32, 32]
    assert n[0] == pytest.approx(0.0, abs=0.05)
    assert n[1] == pytest.approx(0.0, abs=0.05)
    assert n[2] == pytest.approx(1.0, abs=0.01)


def test_empty_alpha_produces_zero_height():
    a = np.zeros((32, 32), dtype=np.float32)
    d = DepthField.from_alpha(a)
    assert np.all(d.height == 0)


def test_full_alpha_produces_flat_center():
    a = np.ones((32, 32), dtype=np.float32)
    d = DepthField.from_alpha(a)
    assert float(d.height[16, 16]) == pytest.approx(1.0)
