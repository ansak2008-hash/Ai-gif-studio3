from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask
from ai_gif_studio.temporal_engine.selective_region import SelectiveRegionEffect

pytestmark = pytest.mark.unit


def _buffer(values: tuple[float, float, float, float]) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[values]], dtype=np.float32)
    )


def _processed(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
    return _buffer((10.0, 20.0, 30.0, 0.25))


def test_selective_region_applies_transform_only_inside_mask() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    effect = SelectiveRegionEffect(
        _processed,
        RenderMask.allocate(1, 1, value=0.25),
    )
    result = effect((source,))
    expected = np.asarray([[[4.0, 8.0, 12.0, 0.6625]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_zero_mask_returns_independent_source_copy() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    result = SelectiveRegionEffect(
        _processed,
        RenderMask.allocate(1, 1, value=0.0),
    )((source,))
    np.testing.assert_array_equal(result.data, source.data)
    assert result is not source


def test_full_mask_returns_independent_processed_copy() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    result = SelectiveRegionEffect(
        _processed,
        RenderMask.allocate(1, 1, value=1.0),
    )((source,))
    np.testing.assert_array_equal(result.data, _processed((source,)).data)


def test_transform_receives_a_copy_and_cannot_mutate_caller_input() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    before = source.data.copy()

    def mutate(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        candidate = inputs[0]
        data = candidate.data.copy()
        data[..., :3] += 5.0
        return RenderBuffer.from_linear_rgba(data)

    SelectiveRegionEffect(
        mutate,
        RenderMask.allocate(1, 1, value=0.5),
    )((source,))
    np.testing.assert_array_equal(source.data, before)


def test_effect_is_structurally_immutable() -> None:
    effect = SelectiveRegionEffect(
        _processed,
        RenderMask.allocate(1, 1, value=1.0),
    )
    with pytest.raises((AttributeError, TypeError)):
        effect.mask = RenderMask.allocate(1, 1, value=0.0)  # type: ignore[misc]


def test_invalid_inputs_and_transform_results_are_rejected() -> None:
    mask = RenderMask.allocate(1, 1, value=1.0)
    with pytest.raises(TypeError, match="transform"):
        SelectiveRegionEffect(object(), mask)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RenderMask"):
        SelectiveRegionEffect(_processed, object())  # type: ignore[arg-type]

    effect = SelectiveRegionEffect(_processed, mask)
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]

    wrong_type = SelectiveRegionEffect(lambda _: object(), mask)
    with pytest.raises(TypeError, match="return"):
        wrong_type((_buffer((1.0, 1.0, 1.0, 1.0)),))

    same_buffer = SelectiveRegionEffect(lambda inputs: inputs[0], mask)
    with pytest.raises(ValueError, match="new RenderBuffer"):
        same_buffer((_buffer((1.0, 1.0, 1.0, 1.0)),))

    wrong_shape = SelectiveRegionEffect(
        lambda _: RenderBuffer.allocate(2, 1),
        mask,
    )
    with pytest.raises(ValueError, match="dimensions"):
        wrong_shape((_buffer((1.0, 1.0, 1.0, 1.0)),))


def test_mask_dimensions_are_rejected_before_transform_execution() -> None:
    called = False

    def process(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
        nonlocal called
        called = True
        return _processed(())

    effect = SelectiveRegionEffect(
        process,
        RenderMask.allocate(2, 1, value=1.0),
    )
    with pytest.raises(ValueError, match="dimensions"):
        effect((_buffer((1.0, 1.0, 1.0, 1.0)),))
    assert called is False


def test_repeated_execution_is_deterministic() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    effect = SelectiveRegionEffect(
        _processed,
        RenderMask.allocate(1, 1, value=0.5),
    )
    first = effect((source,))
    second = effect((source,))
    np.testing.assert_array_equal(first.data, second.data)
