from __future__ import annotations

from uuid import UUID

import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState
from ai_gif_studio.domain.mask_state import MaskState

pytestmark = pytest.mark.unit

MASK_ID = UUID("00000000-0000-0000-0000-000000000001")
EDITED_MASK_ID = UUID("00000000-0000-0000-0000-000000000005")
ASSET_ID = UUID("00000000-0000-0000-0000-000000000002")
EDITED_ASSET_ID = UUID("00000000-0000-0000-0000-000000000006")
LAYER_ID = UUID("00000000-0000-0000-0000-000000000003")
OTHER_LAYER_ID = UUID("00000000-0000-0000-0000-000000000007")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")
OTHER_SOURCE_ID = UUID("00000000-0000-0000-0000-000000000008")


def _stack_with_mask() -> tuple[LayerStack, MaskState]:
    mask = MaskState(MASK_ID, ASSET_ID)
    stack = LayerStack(
        (
            LayerState(LAYER_ID, SOURCE_ID, mask=mask),
            LayerState(OTHER_LAYER_ID, OTHER_SOURCE_ID, opacity=0.5),
        )
    )
    return stack, mask


def test_update_mask_replaces_only_existing_mask_state() -> None:
    stack, mask = _stack_with_mask()
    edited = mask.with_opacity(0.5).with_inverted(True)

    updated = stack.update_mask(LAYER_ID, edited)

    assert updated.layers[0].mask == edited
    assert updated.layers[0].layer_id == LAYER_ID
    assert updated.layers[1] == stack.layers[1]
    assert [layer.layer_id for layer in updated.layers] == [LAYER_ID, OTHER_LAYER_ID]
    assert stack.layers[0].mask == mask


def test_update_mask_preserves_mask_and_source_identity() -> None:
    stack, mask = _stack_with_mask()
    edited = mask.with_blur_radius(8.0)

    updated = stack.update_mask(LAYER_ID, edited)

    assert updated.layers[0].mask is edited
    assert updated.layers[0].mask.mask_id == MASK_ID
    assert updated.layers[0].mask.source_asset_id == ASSET_ID


def test_update_mask_rejects_layer_without_mask() -> None:
    stack = LayerStack((LayerState(LAYER_ID, SOURCE_ID),))
    mask = MaskState(MASK_ID, ASSET_ID)

    with pytest.raises(ValueError, match="has no mask"):
        stack.update_mask(LAYER_ID, mask)


def test_update_mask_rejects_wrong_mask_type() -> None:
    stack, _ = _stack_with_mask()

    with pytest.raises(TypeError, match="MaskState"):
        stack.update_mask(LAYER_ID, object())


def test_update_mask_rejects_mask_identity_change() -> None:
    stack, mask = _stack_with_mask()
    edited = MaskState(EDITED_MASK_ID, ASSET_ID, opacity=0.5)

    with pytest.raises(ValueError, match="mask_id"):
        stack.update_mask(LAYER_ID, edited)

    assert stack.layers[0].mask == mask


def test_update_mask_rejects_source_identity_change() -> None:
    stack, mask = _stack_with_mask()
    edited = MaskState(MASK_ID, EDITED_ASSET_ID, opacity=0.5)

    with pytest.raises(ValueError, match="source_asset_id"):
        stack.update_mask(LAYER_ID, edited)

    assert stack.layers[0].mask == mask


def test_update_mask_unknown_layer_uses_existing_layer_contract() -> None:
    stack, mask = _stack_with_mask()

    with pytest.raises(KeyError, match="unknown layer_id"):
        stack.update_mask(EDITED_MASK_ID, mask)
