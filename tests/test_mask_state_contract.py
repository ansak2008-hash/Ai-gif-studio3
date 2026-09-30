from __future__ import annotations

import json
from uuid import UUID

import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState
from ai_gif_studio.domain.mask_state import (
    MAX_MASK_BLUR_RADIUS,
    MAX_MASK_FEATHER_RADIUS,
    MaskState,
)

pytestmark = pytest.mark.unit

MASK_ID = UUID("00000000-0000-0000-0000-000000000001")
ASSET_ID = UUID("00000000-0000-0000-0000-000000000002")
LAYER_ID = UUID("00000000-0000-0000-0000-000000000003")
SOURCE_ID = UUID("00000000-0000-0000-0000-000000000004")


def test_mask_state_is_immutable_and_asset_referenced() -> None:
    mask = MaskState(MASK_ID, ASSET_ID)
    assert mask.source_asset_id == ASSET_ID
    with pytest.raises(AttributeError):
        mask.inverted = True


@pytest.mark.parametrize("field", ["opacity", "levels_low", "levels_high", "threshold"])
def test_mask_state_rejects_bool_for_numeric_fields(field: str) -> None:
    kwargs = {field: True}
    with pytest.raises(TypeError, match="numeric"):
        MaskState(MASK_ID, ASSET_ID, **kwargs)


@pytest.mark.parametrize("field", ["opacity", "levels_low", "levels_high", "threshold"])
def test_mask_state_rejects_non_finite_numeric_fields(field: str) -> None:
    kwargs = {field: float("nan")}
    with pytest.raises(ValueError, match="finite"):
        MaskState(MASK_ID, ASSET_ID, **kwargs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opacity", -0.01),
        ("opacity", 1.01),
        ("levels_low", -0.01),
        ("levels_high", 1.01),
        ("threshold", -0.01),
        ("threshold", 1.01),
        ("feather_radius", -0.01),
        ("blur_radius", -0.01),
    ],
)
def test_mask_state_rejects_out_of_range_values(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        MaskState(MASK_ID, ASSET_ID, **{field: value})


def test_mask_state_rejects_reversed_levels() -> None:
    with pytest.raises(ValueError, match="levels_low"):
        MaskState(MASK_ID, ASSET_ID, levels_low=0.8, levels_high=0.8)


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("feather_radius", MAX_MASK_FEATHER_RADIUS),
        ("blur_radius", MAX_MASK_BLUR_RADIUS),
    ],
)
def test_mask_state_accepts_radius_boundaries(field: str, maximum: float) -> None:
    mask = MaskState(MASK_ID, ASSET_ID, **{field: maximum})
    assert getattr(mask, field) == maximum


def test_mask_state_rejects_radius_overflow() -> None:
    with pytest.raises(ValueError):
        MaskState(MASK_ID, ASSET_ID, feather_radius=MAX_MASK_FEATHER_RADIUS + 0.01)
    with pytest.raises(ValueError):
        MaskState(MASK_ID, ASSET_ID, blur_radius=MAX_MASK_BLUR_RADIUS + 0.01)


def test_mask_state_canonical_round_trip_is_deterministic() -> None:
    mask = MaskState(
        MASK_ID,
        ASSET_ID,
        enabled=True,
        inverted=True,
        opacity=0.75,
        feather_radius=12.0,
        blur_radius=4.0,
        levels_low=0.1,
        levels_high=0.9,
        threshold=0.5,
    )
    encoded = mask.canonical_json
    assert MaskState.from_canonical_json(encoded) == mask
    assert MaskState.from_canonical_json(encoded).canonical_json == encoded


def test_mask_state_rejects_non_canonical_json() -> None:
    mask = MaskState(MASK_ID, ASSET_ID)
    payload = json.loads(mask.canonical_json)
    with pytest.raises(ValueError, match="normalized"):
        MaskState.from_canonical_json(json.dumps(payload, indent=2))


def test_layer_mask_is_optional_and_legacy_json_remains_valid() -> None:
    layer = LayerState(LAYER_ID, SOURCE_ID)
    stack = LayerStack((layer,))
    legacy = json.dumps(
        {"layers": [dict(layer.metadata)], "max_layers": 256},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert LayerStack.from_canonical_json(legacy) == stack
    assert "mask" not in layer.metadata


def test_layer_mask_round_trip_and_detached_update() -> None:
    layer = LayerState(LAYER_ID, SOURCE_ID)
    stack = LayerStack((layer,))
    mask = MaskState(MASK_ID, ASSET_ID, inverted=True, feather_radius=8.0)
    updated = stack.set_mask(LAYER_ID, mask)

    assert stack.layers[0].mask is None
    assert updated.layers[0].mask == mask
    assert LayerStack.from_canonical_json(updated.canonical_json) == updated


def test_layer_mask_can_be_removed_without_mutating_previous_state() -> None:
    mask = MaskState(MASK_ID, ASSET_ID)
    original = LayerStack((LayerState(LAYER_ID, SOURCE_ID, mask=mask),))
    cleared = original.set_mask(LAYER_ID, None)

    assert original.layers[0].mask == mask
    assert cleared.layers[0].mask is None


def test_mask_state_persistence_rejects_duplicate_json_keys() -> None:
    encoded = (
        '{"mask_id":"00000000-0000-0000-0000-000000000001",'
        '"source_asset_id":"00000000-0000-0000-0000-000000000002",'
        '"enabled":true,"inverted":false,"opacity":1.0,'
        '"feather_radius":0.0,"blur_radius":0.0,"levels_low":0.0,'
        '"levels_high":1.0,"threshold":null,"opacity":0.5}'
    )
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        MaskState.from_canonical_json(encoded)


def test_mask_state_persistence_survives_chained_immutable_edits() -> None:
    original = MaskState(MASK_ID, ASSET_ID)
    edited = (
        original.with_enabled(False)
        .with_inverted(True)
        .with_opacity(0.4)
        .with_feather_radius(16.0)
        .with_blur_radius(8.0)
        .with_levels(0.2, 0.8)
        .with_threshold(0.6)
    )
    restored = MaskState.from_canonical_json(edited.canonical_json)
    assert restored == edited
    assert restored.mask_id == MASK_ID
    assert restored.source_asset_id == ASSET_ID
    assert restored.canonical_json == edited.canonical_json
    assert original == MaskState(MASK_ID, ASSET_ID)
