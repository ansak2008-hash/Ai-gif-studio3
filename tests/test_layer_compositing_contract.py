from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.blend import BlendMode, BlendModeEffect
from ai_gif_studio.temporal_engine.compositor import (
    BlendLayer,
    composite_blend_layers,
    composite_over,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit


def _buffer(rgba: tuple[float, float, float, float]) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(np.array([[rgba]], dtype=np.float32))


def test_single_normal_layer_matches_existing_composite_over() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    source = _buffer((0.6, 0.2, 0.4, 0.75))
    result = composite_blend_layers(base, [BlendLayer(source)])
    expected = composite_over(base, source)
    np.testing.assert_array_equal(result.data, expected.data)


def test_layers_are_composited_in_declared_back_to_front_order() -> None:
    base = _buffer((0.0, 0.0, 1.0, 1.0))
    multiply_layer = BlendLayer(
        _buffer((1.0, 0.5, 0.0, 1.0)),
        mode=BlendMode.MULTIPLY,
    )
    screen_layer = BlendLayer(
        _buffer((0.0, 1.0, 0.5, 0.5)),
        mode=BlendMode.SCREEN,
    )
    result = composite_blend_layers(base, [multiply_layer, screen_layer])
    after_multiply = BlendModeEffect(BlendMode.MULTIPLY)(
        (base, multiply_layer.source)
    )
    expected = composite_over(after_multiply, screen_layer.source)
    np.testing.assert_array_equal(result.data, expected.data)


def test_layer_mask_scales_only_that_layer_alpha() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    source = _buffer((0.6, 0.2, 0.4, 0.75))
    mask = RenderMask.from_array(np.asarray([[0.5]], dtype=np.float32))
    result = composite_blend_layers(base, [BlendLayer(source, mask=mask)])
    masked_source = _buffer((0.6, 0.2, 0.4, 0.375))
    expected = composite_over(base, masked_source)
    np.testing.assert_allclose(result.data, expected.data, rtol=1e-6, atol=1e-7)


def test_empty_layer_sequence_returns_independent_base_copy() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    result = composite_blend_layers(base, [])
    np.testing.assert_array_equal(result.data, base.data)
    assert result is not base


def test_composition_does_not_mutate_or_alias_inputs() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    source = _buffer((0.6, 0.2, 0.4, 0.75))
    base_before = base.data.copy()
    source_before = source.data.copy()
    result = composite_blend_layers(
        base,
        [BlendLayer(source, mode=BlendMode.OVERLAY)],
    )
    np.testing.assert_array_equal(base.data, base_before)
    np.testing.assert_array_equal(source.data, source_before)
    assert result is not base
    assert result is not source


def test_generator_layers_are_supported_deterministically() -> None:
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    layers = (
        BlendLayer(_buffer((0.2, 0.3, 0.4, 1.0))),
        BlendLayer(
            _buffer((0.8, 0.7, 0.6, 0.5)),
            mode=BlendMode.SCREEN,
        ),
    )
    first = composite_blend_layers(base, (layer for layer in layers))
    second = composite_blend_layers(base, (layer for layer in layers))
    np.testing.assert_array_equal(first.data, second.data)


def test_invalid_layer_and_base_types_are_rejected() -> None:
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    with pytest.raises(TypeError, match="base"):
        composite_blend_layers(object(), [])
    with pytest.raises(TypeError, match="BlendLayer"):
        composite_blend_layers(base, [object()])


def test_layer_validates_source_mode_and_mask_types() -> None:
    source = _buffer((0.0, 0.0, 0.0, 1.0))
    with pytest.raises(TypeError, match="source"):
        BlendLayer(object())
    with pytest.raises(TypeError, match="mode"):
        BlendLayer(source, mode="multiply")
    with pytest.raises(TypeError, match="mask"):
        BlendLayer(source, mask=object())


def test_layer_mask_dimensions_are_validated_at_composition_boundary() -> None:
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 1.0, 1.0, 1.0))
    mask = RenderMask.allocate(2, 1, value=1.0)
    with pytest.raises(ValueError, match="mask shape"):
        composite_blend_layers(base, [BlendLayer(source, mask=mask)])
