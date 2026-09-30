from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.mask_state import MaskState


def state() -> MaskState:
    return MaskState(mask_id=uuid4(), source_asset_id=uuid4())


def test_mask_editing_returns_new_state_without_mutating_original() -> None:
    original = state()
    updated = original.with_opacity(0.5)
    assert updated is not original
    assert original.opacity == 1.0
    assert updated.opacity == 0.5
    assert updated.mask_id == original.mask_id
    assert updated.source_asset_id == original.source_asset_id


@pytest.mark.parametrize(("method", "value"), [
    ("with_enabled", False),
    ("with_inverted", True),
    ("with_opacity", 0.25),
    ("with_feather_radius", 12.0),
    ("with_blur_radius", 8.0),
    ("with_levels", (0.2, 0.8)),
    ("with_threshold", 0.6),
])
def test_mask_editing_preserves_unedited_fields(method: str, value: object) -> None:
    original = MaskState(
        mask_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_asset_id=UUID("00000000-0000-0000-0000-000000000002"),
        enabled=False,
        inverted=True,
        opacity=0.7,
        feather_radius=3.0,
        blur_radius=4.0,
        levels_low=0.1,
        levels_high=0.9,
        threshold=0.4,
    )
    updated = getattr(original, method)(*value if isinstance(value, tuple) else (value,))
    assert updated.mask_id == original.mask_id
    assert updated.source_asset_id == original.source_asset_id
    assert updated.enabled == (value if method == "with_enabled" else original.enabled)
    assert updated.inverted == (value if method == "with_inverted" else original.inverted)
    assert updated.opacity == (value if method == "with_opacity" else original.opacity)
    assert updated.feather_radius == (value if method == "with_feather_radius" else original.feather_radius)
    assert updated.blur_radius == (value if method == "with_blur_radius" else original.blur_radius)
    assert updated.threshold == (value if method == "with_threshold" else original.threshold)
    if method == "with_levels":
        assert updated.levels_low == 0.2
        assert updated.levels_high == 0.8
    else:
        assert updated.levels_low == original.levels_low
        assert updated.levels_high == original.levels_high


@pytest.mark.parametrize(("method", "value"), [
    ("with_opacity", -0.1),
    ("with_opacity", 1.1),
    ("with_feather_radius", -1.0),
    ("with_blur_radius", 4096.1),
    ("with_levels", (0.8, 0.2)),
    ("with_threshold", 1.1),
])
def test_mask_editing_reuses_constructor_validation(method: str, value: object) -> None:
    original = state()
    with pytest.raises((TypeError, ValueError)):
        getattr(original, method)(*value if isinstance(value, tuple) else (value,))


def test_with_threshold_none_disables_threshold() -> None:
    original = state().with_threshold(0.5)
    updated = original.with_threshold(None)
    assert original.threshold == 0.5
    assert updated.threshold is None


def test_editing_is_deterministic_and_canonical() -> None:
    original = MaskState(
        mask_id=UUID("00000000-0000-0000-0000-000000000001"),
        source_asset_id=UUID("00000000-0000-0000-0000-000000000002"),
    )
    first = original.with_levels(0.25, 0.75).with_opacity(0.5)
    second = original.with_levels(0.25, 0.75).with_opacity(0.5)
    assert first.canonical_json == second.canonical_json
    assert MaskState.from_canonical_json(first.canonical_json) == first
