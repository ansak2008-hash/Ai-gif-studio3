"""Contract tests for deterministic explicit-time temporal transitions."""
from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.temporal_transitions import TemporalCrossfadeEffect

pytestmark = pytest.mark.unit


def _buffer(rgb: tuple[float, float, float], alpha: float = 1.0) -> RenderBuffer:
    data = np.zeros((2, 2, 4), dtype=np.float32)
    data[..., :3] = rgb
    data[..., 3] = alpha
    return RenderBuffer.from_linear_rgba(data)


def test_temporal_crossfade_interpolates_two_sources() -> None:
    first = _buffer((1.0, 0.0, 0.0))
    second = _buffer((0.0, 0.0, 1.0))

    result = TemporalCrossfadeEffect(0.0, 1.0)((first, second), 0.5)

    expected_rgb = np.broadcast_to(np.array((0.5, 0.0, 0.5), dtype=np.float32), result.data[..., :3].shape)
    np.testing.assert_allclose(result.data[..., :3], expected_rgb)
    np.testing.assert_allclose(result.data[..., 3], 1.0)


def test_temporal_crossfade_interpolates_alpha_without_aliasing() -> None:
    first = _buffer((1.0, 0.0, 0.0), 1.0)
    second = _buffer((0.0, 1.0, 0.0), 0.0)

    result = TemporalCrossfadeEffect(0.0, 1.0)((first, second), 0.25)

    expected_rgb = np.broadcast_to(np.array((1.0, 0.0, 0.0), dtype=np.float32), result.data[..., :3].shape)
    np.testing.assert_allclose(result.data[..., 3], 0.75)
    np.testing.assert_allclose(result.data[..., :3], expected_rgb)
    assert result is not first
    assert result is not second


def test_temporal_crossfade_clamps_endpoints_and_copies_inputs() -> None:
    first = _buffer((1.0, 0.0, 0.0))
    second = _buffer((0.0, 0.0, 1.0))

    before_first = first.data.copy()
    before_second = second.data.copy()

    at_start = TemporalCrossfadeEffect(0.0, 1.0)((first, second), -1.0)
    at_end = TemporalCrossfadeEffect(0.0, 1.0)((first, second), 2.0)

    np.testing.assert_array_equal(at_start.data, first.data)
    np.testing.assert_array_equal(at_end.data, second.data)
    np.testing.assert_array_equal(first.data, before_first)
    np.testing.assert_array_equal(second.data, before_second)
    assert at_start is not first
    assert at_end is not second


def test_temporal_crossfade_is_reusable_and_deterministic() -> None:
    first = _buffer((0.2, 0.4, 0.6), 0.8)
    second = _buffer((0.7, 0.1, 0.3), 0.4)
    effect = TemporalCrossfadeEffect(0.0, 2.0)

    first_result = effect((first, second), 0.75)
    second_result = effect((first, second), 0.75)

    np.testing.assert_array_equal(first_result.data, second_result.data)


def test_temporal_crossfade_rejects_invalid_contracts() -> None:
    first = _buffer((1.0, 0.0, 0.0))
    second = _buffer((0.0, 1.0, 0.0))

    with pytest.raises(ValueError, match="greater"):
        TemporalCrossfadeEffect(1.0, 1.0)
    with pytest.raises(ValueError, match="finite"):
        TemporalCrossfadeEffect(float("nan"), 1.0)
    with pytest.raises(ValueError, match="exactly two"):
        TemporalCrossfadeEffect(0.0, 1.0)((first,), 0.5)
    with pytest.raises(TypeError, match="RenderBuffer"):
        TemporalCrossfadeEffect(0.0, 1.0)((first, object()), 0.5)
    with pytest.raises(ValueError, match="shapes"):
        TemporalCrossfadeEffect(0.0, 1.0)(
            (first, RenderBuffer.from_linear_rgba(np.zeros((3, 2, 4), dtype=np.float32))),
            0.5,
        )
    with pytest.raises(ValueError, match="finite"):
        TemporalCrossfadeEffect(0.0, 1.0)((first, second), float("nan"))


def test_temporal_crossfade_rejects_noncanonical_input_types() -> None:
    with pytest.raises(TypeError, match="RenderBuffer"):
        TemporalCrossfadeEffect(0.0, 1.0)((object(), object()), 0.5)
