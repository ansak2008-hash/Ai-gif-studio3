from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from ai_gif_studio.domain.layer_state import LayerBlendMode, LayerStack, LayerState
from ai_gif_studio.temporal_engine.compositor import BlendLayer, composite_blend_layers
from ai_gif_studio.temporal_engine.layer_binding import bind_layer_stack
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit


def _buffer(value: float) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.full((1, 1, 4), (value, value, value, 1.0), dtype=np.float32)
    )


def _layer(*, opacity: float = 1.0, visible: bool = True, blend_mode: LayerBlendMode = LayerBlendMode.NORMAL) -> LayerState:
    return LayerState(uuid4(), uuid4(), opacity=opacity, visible=visible, blend_mode=blend_mode)


def test_binding_preserves_back_to_front_order_and_source_identity() -> None:
    back = _layer()
    front = _layer()
    back_buffer = _buffer(0.1)
    front_buffer = _buffer(0.9)

    result = bind_layer_stack(
        LayerStack().add(back).add(front),
        {back.source_asset_id: back_buffer, front.source_asset_id: front_buffer},
    )

    assert isinstance(result, tuple)
    assert [item.source for item in result] == [back_buffer, front_buffer]
    assert all(item.mode.value == "normal" for item in result)
    assert all(item.mask is None for item in result)


def test_binding_maps_all_supported_domain_blend_modes_to_temporal_modes() -> None:
    for mode in LayerBlendMode:
        layer = _layer(blend_mode=mode)
        result = bind_layer_stack(
            LayerStack().add(layer),
            {layer.source_asset_id: _buffer(0.7)},
        )
        assert result[0].mode.value == mode.value

def test_invisible_layers_are_skipped_without_reordering_visible_layers() -> None:
    back = _layer()
    hidden = _layer(visible=False)
    front = _layer()

    result = bind_layer_stack(
        LayerStack().add(back).add(hidden).add(front),
        {
            back.source_asset_id: _buffer(0.1),
            hidden.source_asset_id: _buffer(0.5),
            front.source_asset_id: _buffer(0.9),
        },
    )

    assert [item.source.data[0, 0, 0] for item in result] == [0.1, 0.9]


def test_partial_opacity_becomes_canonical_render_mask() -> None:
    layer = _layer(opacity=0.25)
    source = _buffer(0.7)

    result = bind_layer_stack(
        LayerStack().add(layer),
        {layer.source_asset_id: source},
    )

    assert len(result) == 1
    assert isinstance(result[0], BlendLayer)
    assert isinstance(result[0].mask, RenderMask)
    np.testing.assert_array_equal(result[0].mask.data, np.array([[0.25]], dtype=np.float32))


def test_full_opacity_omits_mask() -> None:
    layer = _layer(opacity=1.0)

    result = bind_layer_stack(
        LayerStack().add(layer),
        {layer.source_asset_id: _buffer(0.7)},
    )

    assert result[0].mask is None


def test_missing_source_fails_before_returning_any_binding() -> None:
    layer = _layer()

    with pytest.raises(KeyError, match="source_asset_id"):
        bind_layer_stack(LayerStack().add(layer), {})


def test_invalid_source_mapping_value_fails_closed() -> None:
    layer = _layer()

    with pytest.raises(TypeError, match="RenderBuffer"):
        bind_layer_stack(LayerStack().add(layer), {layer.source_asset_id: object()})


def test_binding_does_not_mutate_source_buffers() -> None:
    layer = _layer(opacity=0.5)
    source = _buffer(0.7)
    before = source.data.copy()

    bind_layer_stack(LayerStack().add(layer), {layer.source_asset_id: source})

    np.testing.assert_array_equal(source.data, before)


def test_binding_rejects_invalid_stack_and_mapping_before_work() -> None:
    with pytest.raises(TypeError, match="LayerStack"):
        bind_layer_stack(object(), {})

    layer = _layer()
    with pytest.raises(TypeError, match="mapping"):
        bind_layer_stack(LayerStack().add(layer), object())


def test_equivalent_inputs_produce_deterministic_binding() -> None:
    first = _layer(opacity=0.3)
    second = _layer(opacity=0.8)
    stack = LayerStack().add(first).add(second)
    sources = {
        first.source_asset_id: _buffer(0.2),
        second.source_asset_id: _buffer(0.8),
    }

    left = bind_layer_stack(stack, sources)
    right = bind_layer_stack(stack, sources)

    assert [(item.source.data.tobytes(), item.mask.data.tobytes() if item.mask else None) for item in left] == [
        (item.source.data.tobytes(), item.mask.data.tobytes() if item.mask else None)
        for item in right
    ]


def test_binding_feeds_existing_compositor_with_layer_opacity() -> None:
    layer = _layer(opacity=0.25)
    source = _buffer(1.0)
    base = _buffer(0.0)

    bound = bind_layer_stack(
        LayerStack().add(layer),
        {layer.source_asset_id: source},
    )
    result = composite_blend_layers(base, bound)

    np.testing.assert_allclose(
        result.data,
        np.array([[[0.25, 0.25, 0.25, 1.0]]], dtype=np.float32),
        rtol=0,
        atol=1e-6,
    )
