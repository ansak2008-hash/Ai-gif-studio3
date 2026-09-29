from __future__ import annotations

import math
from uuid import uuid4

import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState


def _layer(*, opacity: float = 1.0, visible: bool = True) -> LayerState:
    return LayerState(uuid4(), uuid4(), opacity=opacity, visible=visible)


def test_layer_state_is_immutable_and_metadata_is_detached() -> None:
    layer = _layer(opacity=0.5, visible=False)
    with pytest.raises((AttributeError, TypeError)):
        layer.opacity = 0.2
    metadata = layer.metadata
    assert metadata["opacity"] == 0.5
    with pytest.raises(TypeError):
        metadata["opacity"] = 0.2


def test_layer_state_rejects_invalid_identity_and_opacity() -> None:
    with pytest.raises(TypeError):
        LayerState("layer", uuid4())
    with pytest.raises(TypeError):
        LayerState(uuid4(), "asset")
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            LayerState(uuid4(), uuid4(), opacity=value)
    for value in (-0.000001, 1.000001):
        with pytest.raises(ValueError):
            LayerState(uuid4(), uuid4(), opacity=value)
    for value in (True, False):
        with pytest.raises(TypeError):
            LayerState(uuid4(), uuid4(), opacity=value)


def test_layer_state_accepts_opacity_boundaries() -> None:
    assert LayerState(uuid4(), uuid4(), opacity=0.0).opacity == 0.0
    assert LayerState(uuid4(), uuid4(), opacity=1.0).opacity == 1.0


def test_layer_stack_is_immutable_and_ordered_back_to_front() -> None:
    first = _layer()
    second = _layer()
    stack = LayerStack().add(first).add(second)
    assert stack.layers == (first, second)
    with pytest.raises(AttributeError):
        stack.layers.append(first)  # type: ignore[attr-defined]


def test_duplicate_layer_id_is_rejected_without_mutating_stack() -> None:
    layer = _layer()
    stack = LayerStack().add(layer)
    duplicate = LayerState(layer.layer_id, uuid4())
    with pytest.raises(ValueError, match="duplicate layer_id"):
        stack.add(duplicate)
    assert stack.layers == (layer,)


def test_remove_reorder_visibility_and_opacity_return_new_snapshots() -> None:
    first = _layer()
    second = _layer()
    third = _layer()
    stack = LayerStack().add(first).add(second).add(third)
    reordered = stack.move(2, 0)
    assert reordered.layers == (third, first, second)
    hidden = reordered.set_visibility(third.layer_id, False)
    changed = hidden.set_opacity(first.layer_id, 0.25)
    assert hidden.layers[0].visible is False
    assert changed.layers[1].opacity == 0.25
    removed = changed.remove(first.layer_id)
    assert removed.layers == (third, second)
    assert stack.layers == (first, second, third)


@pytest.mark.parametrize("source, target", [(-1, 0), (0, 3), (3, 0), (0, -1)])
def test_move_rejects_invalid_indices(source: int, target: int) -> None:
    stack = LayerStack().add(_layer()).add(_layer()).add(_layer())
    with pytest.raises(IndexError):
        stack.move(source, target)


def test_unknown_layer_id_is_rejected_before_mutation() -> None:
    stack = LayerStack().add(_layer())
    unknown = uuid4()
    with pytest.raises(KeyError):
        stack.remove(unknown)
    with pytest.raises(KeyError):
        stack.set_visibility(unknown, False)
    with pytest.raises(KeyError):
        stack.set_opacity(unknown, 0.5)
    assert len(stack.layers) == 1


def test_stack_has_a_bounded_cardinality() -> None:
    stack = LayerStack(max_layers=2).add(_layer()).add(_layer())
    with pytest.raises(ValueError, match="maximum layer count"):
        stack.add(_layer())


def test_canonical_serialization_is_deterministic_and_round_trips() -> None:
    first = _layer(opacity=0.25, visible=False)
    second = _layer(opacity=1.0, visible=True)
    stack = LayerStack().add(first).add(second)
    canonical = stack.canonical_json
    restored = LayerStack.from_canonical_json(canonical)
    assert restored == stack
    assert restored.canonical_json == canonical


def test_noncanonical_or_duplicate_json_is_rejected() -> None:
    layer = _layer()
    stack = LayerStack().add(layer)
    canonical = stack.canonical_json
    assert LayerStack.from_canonical_json(canonical) == stack
    with pytest.raises(ValueError):
        LayerStack.from_canonical_json(canonical.replace('"layers":', '"x":', 1))
    duplicate = canonical[:-1] + ',"layers":[]}'
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        LayerStack.from_canonical_json(duplicate)


def test_uuid_identity_is_stable_and_source_asset_reference_is_not_owned() -> None:
    asset_id = uuid4()
    layer_id = uuid4()
    layer = LayerState(layer_id, asset_id)
    assert layer.layer_id == layer_id
    assert layer.source_asset_id == asset_id
    assert layer.metadata["source_asset_id"] == str(asset_id)
