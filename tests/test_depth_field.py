import numpy as np
import pytest

from ai_gif_studio.temporal_engine.bevel import BevelProfile
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


def test_sdf_has_negative_outside_and_positive_inside():
    d = DepthField.from_alpha(square_alpha())
    assert float(d.distance_px[0, 0]) < 0.0
    assert float(d.distance_px[32, 32]) > 0.0


def test_height_is_zero_outside_and_flat_inside():
    d = DepthField.from_alpha(square_alpha(), bevel_width_px=8)
    assert np.all(d.height[0] == 0)
    assert float(d.height[32, 16]) < 0.2
    assert float(d.height[32, 32]) == pytest.approx(1.0, abs=1e-6)


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


def test_normals_are_unit_length_on_surface():
    n = DepthField.from_alpha(square_alpha()).normals
    lengths = np.linalg.norm(n, axis=-1)
    assert np.allclose(lengths, 1.0, atol=1e-5)


def test_normals_at_center_are_flat():
    n = DepthField.from_alpha(square_alpha(), bevel_width_px=8).normals[32, 32]
    assert n[0] == pytest.approx(0.0, abs=1e-6)
    assert n[1] == pytest.approx(0.0, abs=1e-6)
    assert n[2] == pytest.approx(1.0, abs=1e-6)


def test_bevel_width_changes_profile():
    a = square_alpha()
    narrow = DepthField.from_alpha(a, bevel_width_px=4)
    wide = DepthField.from_alpha(a, bevel_width_px=16)
    assert float(narrow.height[32, 20]) > float(wide.height[32, 20])


def test_smoothstep_profile_has_zero_boundary_slope():
    profile = BevelProfile(width_px=8.0, power=0.75, smooth=True)
    d = np.array([0.0, 8.0], dtype=np.float32)
    derivative = profile.derivative(d)
    np.testing.assert_allclose(derivative, 0.0, atol=1e-7)


def test_closed_form_chain_rule_matches_field_gradient():
    profile = BevelProfile(width_px=8.0, power=0.75, smooth=True)
    d = np.array([2.0, 4.0, 6.0], dtype=np.float32)

    t = np.clip(d / profile.width_px, 0.0, 1.0)
    u = np.power(t, profile.power)
    expected = (
        6.0
        * u
        * (1.0 - u)
        * profile.power
        * np.power(t, profile.power - 1.0)
        / profile.width_px
    )
    np.testing.assert_allclose(
        profile.derivative(d),
        expected.astype(np.float32),
        rtol=1e-5,
        atol=1e-6,
    )


def test_height_scale_is_dimensionally_applied():
    a = square_alpha()
    low = DepthField.from_alpha(a, height_scale_px=1.0)
    high = DepthField.from_alpha(a, height_scale_px=4.0)
    assert high.normals[32, 17, 0] > low.normals[32, 17, 0]


def test_empty_alpha_produces_zero_height_and_canonical_normals():
    a = np.zeros((32, 32), dtype=np.float32)
    d = DepthField.from_alpha(a)
    assert np.all(d.height == 0)
    np.testing.assert_array_equal(d.normals[..., 0], 0.0)
    np.testing.assert_array_equal(d.normals[..., 1], 0.0)
    np.testing.assert_array_equal(d.normals[..., 2], 1.0)


def test_full_alpha_produces_flat_height_and_normals():
    a = np.ones((32, 32), dtype=np.float32)
    d = DepthField.from_alpha(a)
    assert float(d.height[16, 16]) == pytest.approx(1.0)
    np.testing.assert_allclose(d.normals[16, 16], [0.0, 0.0, 1.0], atol=1e-6)
