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


def test_compositor_releases_render_reservation_on_success() -> None:
    from ai_gif_studio.resources import ResourceManager

    manager = ResourceManager(1024**2)
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 0.0, 0.0, 1.0))
    result = composite_blend_layers(
        base,
        [BlendLayer(source)],
        resource_manager=manager,
    )
    assert result.shape == base.shape
    assert manager.reserved_bytes == 0


def test_compositor_releases_render_reservation_on_failure(monkeypatch) -> None:
    from ai_gif_studio.resources import ResourceManager
    from ai_gif_studio.temporal_engine import compositor

    manager = ResourceManager(1024**2)
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 0.0, 0.0, 1.0))

    def fail(self, inputs):
        raise RuntimeError("injected layer failure")

    monkeypatch.setattr(compositor.BlendModeEffect, "__call__", fail)
    with pytest.raises(RuntimeError, match="injected layer failure"):
        composite_blend_layers(
            base,
            [BlendLayer(source)],
            resource_manager=manager,
        )
    assert manager.reserved_bytes == 0
    np.testing.assert_array_equal(base.data, _buffer((0.0, 0.0, 0.0, 1.0)).data)


def test_compositor_reserves_before_first_output_allocation(monkeypatch) -> None:
    from ai_gif_studio.resources import ResourceManager
    from ai_gif_studio.temporal_engine import compositor

    manager = ResourceManager(1024**2)
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 0.0, 0.0, 1.0))
    requested = manager.estimate_render_memory_bytes(
        base.width,
        base.height,
        1,
        dtype=base.dtype,
    )
    observed: list[int] = []
    original_copy = compositor.RenderBuffer.copy

    def checked_copy(self):
        observed.append(manager.reserved_bytes)
        return original_copy(self)

    monkeypatch.setattr(compositor.RenderBuffer, "copy", checked_copy)
    composite_blend_layers(
        base,
        [BlendLayer(source)],
        resource_manager=manager,
    )
    assert observed
    assert observed[0] == requested
    assert manager.reserved_bytes == 0


def test_composition_preserves_zero_and_full_source_alpha_boundaries() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    transparent = _buffer((1.0, 0.0, 0.0, 0.0))
    opaque = _buffer((0.6, 0.2, 0.4, 1.0))
    transparent_result = composite_blend_layers(base, [BlendLayer(transparent)])
    opaque_result = composite_blend_layers(base, [BlendLayer(opaque)])
    np.testing.assert_array_equal(transparent_result.data, base.data)
    np.testing.assert_array_equal(opaque_result.data, opaque.data)


def test_reversed_layer_order_is_not_silently_normalized() -> None:
    base = _buffer((0.1, 0.1, 0.1, 1.0))
    first = BlendLayer(_buffer((0.8, 0.2, 0.1, 0.75)), mode=BlendMode.MULTIPLY)
    second = BlendLayer(_buffer((0.1, 0.9, 0.3, 0.75)), mode=BlendMode.SCREEN)
    forward = composite_blend_layers(base, [first, second])
    reverse = composite_blend_layers(base, [second, first])
    assert not np.array_equal(forward.data, reverse.data)


def test_insufficient_resource_budget_fails_before_output_allocation(monkeypatch) -> None:
    from ai_gif_studio.resources import ResourceLimitError, ResourceManager
    from ai_gif_studio.temporal_engine import compositor

    manager = ResourceManager(1)
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 0.0, 0.0, 1.0))
    monkeypatch.setattr(
        compositor.RenderBuffer,
        "copy",
        lambda self: pytest.fail("output allocation occurred before admission"),
    )
    with pytest.raises(ResourceLimitError):
        composite_blend_layers(base, [BlendLayer(source)], resource_manager=manager)
    assert manager.reserved_bytes == 0


def test_mask_shape_failure_does_not_publish_output() -> None:
    base = _buffer((0.0, 0.0, 0.0, 1.0))
    source = _buffer((1.0, 0.0, 0.0, 1.0))
    invalid_mask = RenderMask.allocate(2, 1, value=1.0)
    with pytest.raises(ValueError, match="mask shape"):
        composite_blend_layers(base, [BlendLayer(source, mask=invalid_mask)])
    np.testing.assert_array_equal(base.data, _buffer((0.0, 0.0, 0.0, 1.0)).data)


def test_repeated_composition_does_not_mutate_mask_or_inputs() -> None:
    base = _buffer((0.2, 0.4, 0.8, 0.5))
    source = _buffer((0.6, 0.2, 0.4, 0.75))
    mask = RenderMask.from_array(np.asarray([[0.5]], dtype=np.float32))
    before_base = base.data.copy()
    before_source = source.data.copy()
    before_mask = mask.data.copy()
    first = composite_blend_layers(base, [BlendLayer(source, mask=mask)])
    second = composite_blend_layers(base, [BlendLayer(source, mask=mask)])
    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(base.data, before_base)
    np.testing.assert_array_equal(source.data, before_source)
    np.testing.assert_array_equal(mask.data, before_mask)
    assert first.data.base is not second.data.base
