from __future__ import annotations

import json
from uuid import UUID

import numpy as np
import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState
from ai_gif_studio.domain.mask_state import MaskState
from ai_gif_studio.temporal_engine.layer_binding import bind_layer_stack
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit

LAYER_ID = UUID("00000000-0000-0000-0000-000000000001")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000002")
MASK_ID = UUID("00000000-0000-0000-0000-000000000003")
MASK_SOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
OTHER_LAYER_ID = UUID("00000000-0000-0000-0000-000000000005")
OTHER_SOURCE_ID = UUID("00000000-0000-0000-0000-000000000006")


def _mask() -> MaskState:
    return MaskState(MASK_ID, MASK_SOURCE_ID)


def _stack(mask: MaskState | None = None) -> LayerStack:
    return LayerStack(
        (
            LayerState(LAYER_ID, SOURCE_ID, opacity=0.7, mask=mask),
            LayerState(OTHER_LAYER_ID, OTHER_SOURCE_ID, opacity=0.4),
        ),
        max_layers=8,
    )


def _render_mask() -> RenderMask:
    return RenderMask.from_array(
        np.array([[0.0, 0.25], [0.75, 1.0]], dtype=np.float32)
    )


def test_mask_lifecycle_attach_edit_round_trip_and_remove() -> None:
    original = _stack()
    attached = original.set_mask(LAYER_ID, _mask())
    edited_mask = attached.layers[0].mask.with_opacity(0.5).with_inverted(True)
    edited = attached.update_mask(LAYER_ID, edited_mask)
    restored = LayerStack.from_canonical_json(edited.canonical_json)
    removed = restored.set_mask(LAYER_ID, None)

    assert original.layers[0].mask is None
    assert attached.layers[0].mask == _mask()
    assert edited.layers[0].mask == edited_mask
    assert restored == edited
    assert removed.layers[0].mask is None
    assert removed.layers[1] == original.layers[1]
    assert removed.max_layers == original.max_layers


def test_set_mask_replacement_is_immutable_and_preserves_layer_properties() -> None:
    original_mask = _mask()
    replacement = MaskState(\n        UUID("00000000-0000-0000-0000-000000000007"),\n        UUID("00000000-0000-0000-0000-000000000008"),\n    )
    original = _stack(original_mask)
    replaced = original.set_mask(LAYER_ID, replacement)

    assert original.layers[0].mask is original_mask
    assert replaced.layers[0].mask is replacement
    assert replaced.layers[0].layer_id == original.layers[0].layer_id
    assert replaced.layers[0].source_asset_id == original.layers[0].source_asset_id
    assert replaced.layers[0].opacity == original.layers[0].opacity
    assert replaced.layers[0].visible is original.layers[0].visible
    assert replaced.layers[0].blend_mode is original.layers[0].blend_mode
    assert replaced.layers[1] == original.layers[1]
    assert replaced.max_layers == original.max_layers


def test_update_mask_rejects_identity_replacement_but_set_mask_can_attach_new_state() -> None:
    original = _stack(_mask())
    replacement = MaskState(\n        UUID("00000000-0000-0000-0000-000000000009"),\n        UUID("00000000-0000-0000-0000-00000000000a"),\n    )
    with pytest.raises(ValueError, match="mask_id"):
        original.update_mask(LAYER_ID, replacement)
    replaced = original.set_mask(LAYER_ID, replacement)
    assert replaced.layers[0].mask == replacement
    assert original.layers[0].mask == _mask()


def test_mask_lifecycle_legacy_unmasked_json_remains_readable() -> None:
    payload = {
        "layers": [
            {
                "layer_id": str(LAYER_ID),
                "source_asset_id": str(SOURCE_ID),
                "opacity": 0.7,
                "visible": True,
                "blend_mode": "normal",
            }
        ],
        "max_layers": 8,
    }
    encoded = json.dumps(\n        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")\n    )
    restored = LayerStack.from_canonical_json(encoded)
    assert restored.layers[0].mask is None
    assert restored.canonical_json == encoded


def test_mask_lifecycle_restored_state_binds_identically() -> None:
    stack = _stack(_mask())
    edited = stack.update_mask(LAYER_ID, stack.layers[0].mask.with_feather_radius(1.0))
    restored = LayerStack.from_canonical_json(edited.canonical_json)
    sources = {
        SOURCE_ID: RenderBuffer.allocate(2, 2),
        OTHER_SOURCE_ID: RenderBuffer.allocate(2, 2),
    }
    masks = {MASK_SOURCE_ID: _render_mask()}

    first = bind_layer_stack(edited, sources, masks=masks)
    second = bind_layer_stack(restored, sources, masks=masks)

    assert first[0].mode is second[0].mode
    np.testing.assert_array_equal(first[0].mask.data, second[0].mask.data)


def test_mask_lifecycle_binding_does_not_mutate_caller_owned_mask() -> None:
    stack = _stack(_mask())
    source_mask = _render_mask()
    before = source_mask.data.copy()
    bind_layer_stack(
        stack,
        {
            SOURCE_ID: RenderBuffer.allocate(2, 2),
            OTHER_SOURCE_ID: RenderBuffer.allocate(2, 2),
        },
        masks={MASK_SOURCE_ID: source_mask},
    )
    np.testing.assert_array_equal(source_mask.data, before)


def test_mask_lifecycle_missing_mask_source_fails_closed() -> None:
    stack = _stack(_mask())
    with pytest.raises(KeyError, match="mask source_asset_id not found"):
        bind_layer_stack(
            stack,
            {
                SOURCE_ID: RenderBuffer.allocate(2, 2),
                OTHER_SOURCE_ID: RenderBuffer.allocate(2, 2),
            },
            masks={},
        )


def test_mask_lifecycle_wrong_mask_source_type_fails_closed() -> None:
    stack = _stack(_mask())
    with pytest.raises(TypeError, match="RenderMask"):
        bind_layer_stack(
            stack,
            {
                SOURCE_ID: RenderBuffer.allocate(2, 2),
                OTHER_SOURCE_ID: RenderBuffer.allocate(2, 2),
            },
            masks={MASK_SOURCE_ID: object()},
        )


def test_mask_lifecycle_unknown_layer_and_missing_mask_fail_deterministically() -> None:
    stack = _stack()
    with pytest.raises(KeyError, match="unknown layer_id"):
        stack.set_mask(OTHER_SOURCE_ID, _mask())
    with pytest.raises(ValueError, match="has no mask"):
        stack.update_mask(LAYER_ID, _mask())
