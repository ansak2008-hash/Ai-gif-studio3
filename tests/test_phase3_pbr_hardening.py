from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.material_pbr import (
    DirectLight,
    PBRMaterial,
    shade_pbr,
    shade_pbr_lights,
)

pytestmark = pytest.mark.unit


def _scene() -> tuple[np.ndarray, np.ndarray, PBRMaterial, DirectLight]:
    normal = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    view = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    material = PBRMaterial((0.72, 0.48, 0.22), roughness=0.42, metallic=0.15)
    light = DirectLight((0.0, 0.0, 1.0), (1.0, 0.9, 0.8), 0.8)
    return normal, view, material, light


def test_legacy_single_light_is_bit_identical_to_scene_contract():
    normal, view, material, light = _scene()

    legacy = shade_pbr(
        normal,
        view,
        light.direction,
        material.albedo,
        material.roughness,
        metallic=material.metallic,
        light_color=light.color,
        light_intensity=light.intensity,
    )
    contract = shade_pbr_lights(normal, view, (light,), material)

    np.testing.assert_array_equal(legacy, contract)


def test_multi_light_accumulation_is_exact_sum_before_post_processing():
    normal, view, material, first = _scene()
    second = DirectLight((0.2, 0.1, 1.0), (0.4, 0.7, 1.0), 0.5)
    third = DirectLight((-0.3, 0.2, 1.0), (1.0, 0.3, 0.2), 0.25)

    one = shade_pbr_lights(normal, view, (first,), material)
    two = shade_pbr_lights(normal, view, (first, second), material)
    three = shade_pbr_lights(normal, view, (first, second, third), material)

    second_only = shade_pbr_lights(normal, view, (second,), material)
    third_only = shade_pbr_lights(normal, view, (third,), material)

    np.testing.assert_array_equal(two, one + second_only)
    np.testing.assert_array_equal(three, two + third_only)


def test_multi_light_order_is_explicit_and_deterministic():
    normal, view, material, first = _scene()
    second = DirectLight((0.2, 0.1, 1.0), (0.4, 0.7, 1.0), 0.5)
    third = DirectLight((-0.3, 0.2, 1.0), (1.0, 0.3, 0.2), 0.25)

    forward = shade_pbr_lights(normal, view, (first, second, third), material)
    reverse = shade_pbr_lights(normal, view, (third, second, first), material)

    np.testing.assert_allclose(forward, reverse, rtol=0.0, atol=2e-15)


def test_empty_lights_are_rejected_explicitly():
    normal, view, material, _ = _scene()

    with pytest.raises(ValueError, match="at least one DirectLight"):
        shade_pbr_lights(normal, view, (), material)


def test_invalid_light_members_are_rejected_explicitly():
    normal, view, material, _ = _scene()

    with pytest.raises(TypeError, match="DirectLight"):
        shade_pbr_lights(normal, view, (object(),), material)


def test_missing_material_is_rejected_by_scene_contract():
    normal, view, _, light = _scene()

    with pytest.raises(TypeError, match="PBRMaterial"):
        shade_pbr_lights(normal, view, (light,), None)  # type: ignore[arg-type]


def test_invalid_direct_light_values_are_rejected_at_construction():
    with pytest.raises(ValueError, match="non-negative"):
        DirectLight((0.0, 0.0, 1.0), intensity=-1.0)

    with pytest.raises(ValueError, match="finite"):
        DirectLight((0.0, 0.0, 1.0), intensity=float("nan"))

    with pytest.raises(ValueError, match="finite"):
        DirectLight((0.0, 0.0, 1.0), color=(1.0, float("nan"), 1.0))


def test_pbr_material_is_immutable():
    material = PBRMaterial((0.8, 0.3, 0.1), roughness=0.35, metallic=0.2)
    before = material

    normal = view = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    light = DirectLight((0.0, 0.0, 1.0), intensity=2.0)
    _ = shade_pbr_lights(normal, view, (light,), material)

    assert material == before
    with pytest.raises(AttributeError):
        material.roughness = 0.5  # type: ignore[misc]
