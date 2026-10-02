from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.commands import (
    AddLayerCommand,
    DuplicateLayerCommand,
    RemoveLayerCommand,
    ReorderLayerCommand,
    SetLayerBlendModeCommand,
    SetLayerOpacityCommand,
    SetLayerVisibilityCommand,
)
from ai_gif_studio.domain.layer_state import LayerBlendMode, LayerState, LayerStack

pytestmark = pytest.mark.unit


def _layer(*, layer_id: UUID | None = None, source_asset_id: UUID | None = None) -> LayerState:
    return LayerState(
        layer_id or uuid4(),
        source_asset_id or uuid4(),
        opacity=0.75,
        visible=True,
        blend_mode=LayerBlendMode.MULTIPLY,
    )


def test_add_layer_command_preserves_existing_layers_and_adds_one() -> None:
    from ai_gif_studio.domain.project import ProjectState

    initial = ProjectState(layer_stack=LayerStack((_layer(),)))
    added = _layer()
    result = AddLayerCommand(added).apply(initial)
    assert len(result.layer_stack.layers) == 2
    assert result.layer_stack.layers[0] == initial.layer_stack.layers[0]
    assert result.layer_stack.layers[1] == added
    assert result.revision == initial.revision + 1


def test_remove_layer_command_rejects_unknown_identity() -> None:
    from ai_gif_studio.domain.project import ProjectState

    initial = ProjectState(layer_stack=LayerStack((_layer(),)))
    with pytest.raises(KeyError):
        RemoveLayerCommand(uuid4()).apply(initial)
    assert initial.revision == 0


def test_reorder_preserves_identity_and_payload() -> None:
    from ai_gif_studio.domain.project import ProjectState

    first = _layer()
    second = _layer()
    initial = ProjectState(layer_stack=LayerStack((first, second)))
    result = ReorderLayerCommand(0, 1).apply(initial)
    assert result.layer_stack.layers == (second, first)
    assert result.layer_stack.layers[0].layer_id == second.layer_id
    assert result.layer_stack.layers[1].source_asset_id == first.source_asset_id


@pytest.mark.parametrize("opacity", [True, float("nan"), float("inf"), -0.01, 1.01])
def test_opacity_boundaries_are_rejected(opacity: object) -> None:
    from ai_gif_studio.domain.project import ProjectState

    initial = ProjectState(layer_stack=LayerStack((_layer(),)))
    with pytest.raises((TypeError, ValueError)):
        SetLayerOpacityCommand(initial.layer_stack.layers[0].layer_id, opacity).apply(initial)


def test_duplicate_creates_explicit_distinct_identity() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,)))
    result = DuplicateLayerCommand(original.layer_id, uuid4()).apply(initial)
    duplicate = result.layer_stack.layers[1]
    assert duplicate.layer_id != original.layer_id
    assert duplicate.source_asset_id == original.source_asset_id
    assert duplicate.opacity == original.opacity
    assert duplicate.visible == original.visible
    assert duplicate.blend_mode == original.blend_mode


def test_visibility_and_blend_mode_are_typed() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,)))
    assert SetLayerVisibilityCommand(original.layer_id, False).apply(initial).layer_stack.layers[0].visible is False
    assert SetLayerBlendModeCommand(original.layer_id, LayerBlendMode.SCREEN).apply(initial).layer_stack.layers[0].blend_mode is LayerBlendMode.SCREEN


def test_failed_command_does_not_change_revision() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,)))
    with pytest.raises(KeyError):
        SetLayerVisibilityCommand(uuid4(), False).apply(initial)
    assert initial.layer_stack.layers == (original,)
    assert initial.revision == 0


def test_add_rejects_duplicate_identity_and_maximum_boundary() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,), max_layers=1))
    with pytest.raises(ValueError):
        AddLayerCommand(original).apply(initial)
    with pytest.raises(ValueError):
        AddLayerCommand(_layer()).apply(initial)
    assert initial.revision == 0


def test_duplicate_preserves_mask_and_inserts_adjacent_to_source() -> None:
    from ai_gif_studio.domain.mask_state import MaskState
    from ai_gif_studio.domain.project import ProjectState

    first = _layer()
    second = _layer()
    mask = MaskState(uuid4(), uuid4())
    first = LayerState(
        first.layer_id,
        first.source_asset_id,
        first.opacity,
        first.visible,
        first.blend_mode,
        mask,
    )
    initial = ProjectState(layer_stack=LayerStack((first, second)))
    duplicate_id = uuid4()
    result = DuplicateLayerCommand(first.layer_id, duplicate_id).apply(initial)
    assert tuple(layer.layer_id for layer in result.layer_stack.layers) == (
        first.layer_id,
        duplicate_id,
        second.layer_id,
    )
    assert result.layer_stack.layers[1].mask == first.mask


def test_invalid_blend_mode_is_rejected_before_state_change() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,)))
    with pytest.raises(TypeError):
        SetLayerBlendModeCommand(original.layer_id, "screen").apply(initial)
    assert initial.layer_stack.layers == (original,)
    assert initial.revision == 0


def test_commands_are_immutable() -> None:
    command = ReorderLayerCommand(0, 1)
    with pytest.raises(AttributeError):
        command.source = 1


def test_failed_reorder_does_not_change_state() -> None:
    from ai_gif_studio.domain.project import ProjectState

    original = _layer()
    initial = ProjectState(layer_stack=LayerStack((original,)))
    with pytest.raises(IndexError):
        ReorderLayerCommand(0, 1).apply(initial)
    assert initial.layer_stack.layers == (original,)
    assert initial.revision == 0
