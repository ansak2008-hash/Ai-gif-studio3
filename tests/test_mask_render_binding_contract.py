from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState
from ai_gif_studio.domain.mask_state import MaskState
from ai_gif_studio.temporal_engine.layer_binding import bind_layer_stack
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask


def buffer(width: int = 2, height: int = 2) -> RenderBuffer:
    return RenderBuffer.allocate(width, height)


def mask(values: list[list[float]]) -> RenderMask:
    return RenderMask.from_array(np.asarray(values, dtype=np.float32))


def state(source_asset_id: object, **overrides: object) -> MaskState:
    values: dict[str, object] = {
        "mask_id": uuid4(),
        "source_asset_id": source_asset_id,
    }
    values.update(overrides)
    return MaskState(**values)


def test_binding_materializes_persistent_mask_and_preserves_mask_semantics() -> None:
    source_id = uuid4()
    mask_id = uuid4()
    layer = LayerState(uuid4(), source_id, mask=state(mask_id, opacity=0.5))
    stack = LayerStack((layer,))
    bindings = bind_layer_stack(
        stack,
        {source_id: buffer()},
        masks={mask_id: mask([[0.0, 0.25], [0.75, 1.0]])},
    )
    assert bindings[0].mask is not None
    np.testing.assert_array_equal(
        bindings[0].mask.data,
        np.array([[0.0, 0.125], [0.375, 0.5]], dtype=np.float32),
    )


def test_layer_opacity_multiplies_persistent_mask() -> None:
    source_id = uuid4()
    mask_id = uuid4()
    layer = LayerState(uuid4(), source_id, opacity=0.5, mask=state(mask_id))
    binding = bind_layer_stack(
        LayerStack((layer,)),
        {source_id: buffer()},
        masks={mask_id: mask([[0.0, 0.25], [0.75, 1.0]])},
    )[0]
    assert binding.mask is not None
    np.testing.assert_array_equal(
        binding.mask.data,
        np.array([[0.0, 0.125], [0.375, 0.5]], dtype=np.float32),
    )


def test_mask_dimensions_must_match_source() -> None:
    source_id = uuid4()
    mask_id = uuid4()
    layer = LayerState(uuid4(), source_id, mask=state(mask_id))
    with pytest.raises(ValueError, match="mask dimensions"):
        bind_layer_stack(
            LayerStack((layer,)),
            {source_id: buffer(2, 2)},
            masks={mask_id: mask([[1.0]])},
        )


def test_persistent_mask_requires_explicit_resolution_mapping() -> None:
    source_id = uuid4()
    layer = LayerState(uuid4(), source_id, mask=state(uuid4()))
    with pytest.raises(KeyError, match="mask source_asset_id not found"):
        bind_layer_stack(LayerStack((layer,)), {source_id: buffer()}, masks={})


def test_persistent_mask_is_not_silently_ignored_when_mapping_is_omitted() -> None:
    source_id = uuid4()
    layer = LayerState(uuid4(), source_id, mask=state(uuid4()))
    with pytest.raises(ValueError, match="mask resolution mapping is required"):
        bind_layer_stack(LayerStack((layer,)), {source_id: buffer()})


def test_unmasked_legacy_binding_remains_unchanged() -> None:
    source_id = uuid4()
    binding = bind_layer_stack(
        LayerStack((LayerState(uuid4(), source_id),)),
        {source_id: buffer()},
    )[0]
    assert binding.mask is None


def test_disabled_persistent_mask_resolves_to_identity_before_layer_opacity() -> None:
    source_id = uuid4()
    mask_id = uuid4()
    layer = LayerState(uuid4(), source_id, opacity=0.25, mask=state(mask_id, enabled=False))
    binding = bind_layer_stack(
        LayerStack((layer,)),
        {source_id: buffer()},
        masks={mask_id: mask([[0.0, 0.2], [0.8, 1.0]])},
    )[0]
    assert binding.mask is not None
    np.testing.assert_array_equal(
        binding.mask.data,
        np.full((2, 2), 0.25, dtype=np.float32),
    )
