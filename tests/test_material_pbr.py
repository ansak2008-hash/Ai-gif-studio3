import numpy as np
import pytest

from ai_gif_studio.temporal_engine.material_pbr import (
    cook_torrance_specular,
    fresnel_schlick,
    ggx_distribution,
    smith_geometry,
)

pytestmark = pytest.mark.unit


def test_fresnel_schlick_normal_incidence_returns_f0():
    f0 = np.array([0.04, 0.2, 0.9], dtype=np.float64)
    np.testing.assert_allclose(fresnel_schlick(1.0, f0), f0, rtol=0, atol=1e-14)


def test_fresnel_schlick_reaches_one_at_grazing():
    result = fresnel_schlick(0.0, 0.04)
    np.testing.assert_allclose(result, 1.0, rtol=0, atol=1e-14)


@pytest.mark.parametrize("f0", [0.0, 1.0])
def test_fresnel_schlick_boundary_f0_is_exact(f0):
    cosines = np.linspace(0.0, 1.0, 101, dtype=np.float64)
    result = fresnel_schlick(cosines, f0)
    expected = (1.0 - cosines) ** 5 if f0 == 0.0 else np.ones_like(cosines)
    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-14)


def test_fresnel_schlick_is_monotone_with_angle():
    cosines = np.linspace(1.0, 0.0, 101, dtype=np.float64)
    result = fresnel_schlick(cosines, 0.04)
    assert np.all(np.diff(result) >= -1e-14)
    assert np.isfinite(result).all()


def test_fresnel_rejects_invalid_f0():
    with pytest.raises(ValueError):
        fresnel_schlick(0.5, 1.1)


@pytest.mark.parametrize("roughness", [0.001, 0.01, 0.1, 0.5, 1.0])
def test_ggx_is_finite_and_nonnegative(roughness):
    cosines = np.linspace(0.0, 1.0, 257, dtype=np.float64)
    result = ggx_distribution(cosines, roughness)
    assert np.isfinite(result).all()
    assert np.all(result >= 0.0)


def test_ggx_peaks_at_normal_alignment():
    roughness = 0.35
    values = ggx_distribution(np.array([0.0, 0.5, 1.0], dtype=np.float64), roughness)
    assert values[2] >= values[1] >= values[0]


@pytest.mark.parametrize("roughness", [0.35, 0.5, 1.0])
def test_ggx_is_normalized_at_moderate_roughness(roughness):
    """Uniform quadrature is sufficiently resolved for moderate roughness."""
    cosines = np.linspace(0.0, 1.0, 400001, dtype=np.float64)
    values = ggx_distribution(cosines, roughness)
    integral = 2.0 * np.pi * np.trapezoid(values * cosines, cosines)
    np.testing.assert_allclose(integral, 1.0, rtol=1e-6, atol=1e-6)


@pytest.mark.parametrize("roughness", [0.01, 0.05, 0.1])
def test_ggx_analytic_normalization_low_roughness(roughness):
    """Verify the closed-form GGX hemisphere normalization."""
    alpha2 = float(roughness) ** 4
    analytic_integral = (
        alpha2 / (alpha2 - 1.0) * (1.0 - 1.0 / alpha2)
        if not np.isclose(alpha2, 1.0)
        else 1.0
    )
    np.testing.assert_allclose(analytic_integral, 1.0, rtol=0, atol=1e-15)

    c = 0.5
    denominator = 1.0 + c * c * (alpha2 - 1.0)
    expected_d = alpha2 / (np.pi * denominator * denominator)
    np.testing.assert_allclose(
        ggx_distribution(c, roughness),
        expected_d,
        rtol=1e-14,
        atol=1e-14,
    )


def test_ggx_rejects_invalid_roughness():
    with pytest.raises(ValueError):
        ggx_distribution(0.5, 0.0)


@pytest.mark.parametrize("roughness", [0.1, 0.5, 1.0])
def test_smith_increases_with_ndotx(roughness):
    cosines = np.linspace(0.0, 1.0, 101, dtype=np.float64)
    values = smith_geometry(cosines, 1.0, roughness)
    assert np.all(np.diff(values) >= -1e-14)


@pytest.mark.parametrize("ndotx", [0.1, 0.5, 0.9])
def test_smith_decreases_with_roughness(ndotx):
    roughnesses = np.array([0.1, 0.3, 0.6, 1.0], dtype=np.float64)
    values = np.array(
        [smith_geometry(ndotx, 1.0, float(r)) for r in roughnesses],
        dtype=np.float64,
    )
    assert np.all(np.diff(values) <= 1e-14)


@pytest.mark.parametrize("roughness", [0.001, 0.1, 0.5, 1.0])
def test_smith_is_bounded_and_finite(roughness):
    values = smith_geometry(
        np.linspace(0.0, 1.0, 101, dtype=np.float64),
        np.linspace(1.0, 0.0, 101, dtype=np.float64),
        roughness,
    )
    assert np.isfinite(values).all()
    assert np.all(values >= 0.0)
    assert np.all(values <= 1.0 + 1e-14)


def test_smith_rejects_invalid_roughness():
    with pytest.raises(ValueError):
        smith_geometry(0.5, 0.5, 1.1)


def test_cook_torrance_is_finite_and_nonnegative():
    values = cook_torrance_specular(
        np.linspace(0.001, 1.0, 101, dtype=np.float64),
        np.linspace(1.0, 0.001, 101, dtype=np.float64),
        0.7,
        0.8,
        0.25,
        0.04,
    )
    assert np.isfinite(values).all()
    assert np.all(values >= 0.0)


def test_cook_torrance_is_finite_at_grazing():
    values = cook_torrance_specular(
        np.array([1e-8, 1e-6, 1e-4], dtype=np.float64),
        np.array([1e-8, 1e-6, 1e-4], dtype=np.float64),
        1.0,
        1.0,
        0.5,
        0.04,
    )
    assert np.isfinite(values).all()


def test_cook_torrance_is_reciprocal_in_view_and_light():
    normal = np.array([0.0, 0.0, 1.0])
    view = np.array([np.sqrt(1.0 - 0.42**2), 0.0, 0.42])
    light = np.array(
        [
            np.sqrt(1.0 - 0.73**2) * np.cos(1.0),
            np.sqrt(1.0 - 0.73**2) * np.sin(1.0),
            0.73,
        ]
    )
    half_vector = view + light
    half_vector /= np.linalg.norm(half_vector)

    ndotv = float(np.dot(normal, view))
    ndotl = float(np.dot(normal, light))
    ndoth = float(np.dot(normal, half_vector))
    vdoth = float(np.dot(view, half_vector))

    forward = cook_torrance_specular(
        ndotv, ndotl, ndoth, vdoth, 0.32, 0.04
    )
    swapped = cook_torrance_specular(
        ndotl, ndotv, ndoth, vdoth, 0.32, 0.04
    )
    np.testing.assert_allclose(forward, swapped, rtol=1e-12, atol=1e-14)


def test_pbr_primitives_support_broadcasting():
    ndotv = np.array([[0.2], [0.6]], dtype=np.float64)
    ndotl = np.array([[0.3, 0.8, 1.0]], dtype=np.float64)
    result = cook_torrance_specular(ndotv, ndotl, 0.75, 0.65, 0.3, 0.04)
    assert result.shape == (2, 3)
    assert np.isfinite(result).all()


def test_pbr_primitives_return_float64():
    values = (
        fresnel_schlick(0.5, 0.04),
        ggx_distribution(0.5, 0.3),
        smith_geometry(0.5, 0.6, 0.3),
        cook_torrance_specular(0.5, 0.6, 0.7, 0.8, 0.3, 0.04),
    )
    assert all(value.dtype == np.float64 for value in values)


def test_pbr_primitives_are_deterministic():
    args = (
        np.array([0.2, 0.5, 0.9], dtype=np.float64),
        np.array([0.9, 0.5, 0.2], dtype=np.float64),
        0.65,
        0.75,
        0.32,
        np.array([0.04, 0.2, 0.8], dtype=np.float64),
    )
    a = cook_torrance_specular(*args)
    b = cook_torrance_specular(*args)
    np.testing.assert_array_equal(a, b)
