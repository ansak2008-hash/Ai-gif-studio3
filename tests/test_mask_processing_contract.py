from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from ai_gif_studio.domain.mask_state import MaskState
from ai_gif_studio.temporal_engine.mask_processing import process_mask
from ai_gif_studio.temporal_engine.render_mask import RenderMask


def make_state(**overrides: object) -> MaskState:
    values: dict[str, object] = {
        "mask_id": uuid4(),
        "source_asset_id": uuid4(),
    }
    values.update(overrides)
    return MaskState(**values)


def render(values: list[list[float]]) -> RenderMask:
    return RenderMask.from_array(np.asarray(values, dtype=np.float32))


def test_disabled_mask_is_identity_and_skips_all_operations() -> None:
    source = render([[0.0, 0.25], [0.75, 1.0]])
    state = make_state(enabled=False, inverted=True, opacity=0.2, threshold=0.5, levels_low=0.2, levels_high=0.8)
    result = process_mask(source, state)
    np.testing.assert_array_equal(result.data, np.ones((2, 2), dtype=np.float32))


def test_levels_are_applied_before_threshold_inversion_and_opacity() -> None:
    source = render([[0.0, 0.5, 1.0]])
    state = make_state(levels_low=0.25, levels_high=0.75, threshold=0.5, inverted=True, opacity=0.5)
    result = process_mask(source, state)
    np.testing.assert_array_equal(result.data, np.array([[0.5, 0.5, 0.0]], dtype=np.float32))


def test_threshold_is_lower_exclusive_and_upper_inclusive() -> None:
    source = render([[0.49, 0.5, 0.51]])
    state = make_state(threshold=0.5)
    result = process_mask(source, state)
    np.testing.assert_array_equal(result.data, np.array([[0.0, 1.0, 1.0]], dtype=np.float32))


def test_spatial_stage_is_deterministic_and_does_not_mutate_source() -> None:
    source = render([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]])
    before = source.data.copy()
    state = make_state(feather_radius=1.0, blur_radius=1.0)
    first = process_mask(source, state)
    second = process_mask(source, state)
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(first.data, second.data)
    assert first.data.dtype == np.float32
    assert first.data.flags.writeable is False
    assert 0.0 < float(first.data[1, 1]) < 1.0


def test_zero_spatial_radius_preserves_values_before_other_operations() -> None:
    source = render([[0.0, 0.25, 0.75, 1.0]])
    result = process_mask(source, make_state())
    np.testing.assert_array_equal(result.data, source.data)


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -1.0])
def test_process_mask_rejects_invalid_source_type_or_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        process_mask(value, make_state())


def test_process_mask_rejects_mask_state_type() -> None:
    with pytest.raises(TypeError):
        process_mask(render([[0.0]]), object())


def test_large_spatial_radii_are_bounded_without_kernel_allocation_explosion() -> None:
    source = render([[1.0]])
    result = process_mask(source, make_state(feather_radius=4096.0, blur_radius=4096.0))
    np.testing.assert_array_equal(result.data, np.ones((1, 1), dtype=np.float32))
