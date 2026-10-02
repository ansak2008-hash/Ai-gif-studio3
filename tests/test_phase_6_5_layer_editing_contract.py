from __future__ import annotations

import math
from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.commands import (
    AddLayerCommand,
    DuplicateLayerCommand,
    ReorderLayerCommand,
    RemoveLayerCommand,
    SetLayerBlendModeCommand,
    SetLayerOpacityCommand,
    SetLayerVisibilityCommand,
)
from ai_gif_studio.domain.layer_state import LayerBlendMode, LayerStack, LayerState
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.services.project_editor import ProjectEditor


pytestmark = pytest.mark.unit


def _state(stack: LayerStack | None = None) -> ProjectState:
    return ProjectState(
        uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {"marker": "preserved"},
        layer_stack=stack,
    )


def _layer(*, source_asset_id: UUID | None = None) -> LayerState:
    return LayerState(uuid4(), source_asset_id or uuid4(), opacity=0.25, visible=False, blend_mode=LayerBlendMode.SCREEN)


def _editor(stack: LayerStack | None = None) -> ProjectEditor:
    return ProjectEditor.create(_state(stack))


def test_add_layer_command_creates_one_revision_and_preserves_unrelated_state() -> None:
    editor = _editor()
    layer = _layer()
    result = editor.execute(AddLayerCommand(layer), {"operation": "add_layer"})
    assert result.revision == 1
    assert editor.revision_count == 2
    assert result.layer_stack.layers == (layer,)
    assert result.metadata == {"marker": "preserved"}


def test_remove_layer_command_preserves_remaining_identity_and_order() -> None:
    first = _layer()
    second = _layer()
    third = _layer()
    editor = _editor(LayerStack().add(first).add(second).add(third))
    result = editor.execute(RemoveLayerCommand(second.layer_id), {"operation": "remove_layer"})
    assert result.layer_stack.layers == (first, third)


def test_duplicate_layer_command_requires_explicit_new_identity_and_preserves_properties() -> None:
    source_asset_id = uuid4()
    original = _layer(source_asset_id=source_asset_id)
    editor = _editor(LayerStack().add(original))
    new_layer_id = uuid4()
    result = editor.execute(
        DuplicateLayerCommand(original.layer_id, new_layer_id),
        {"operation": "duplicate_layer"},
    )
    duplicate = result.layer_stack.layers[1]
    assert duplicate.layer_id == new_layer_id
    assert duplicate.layer_id != original.layer_id
    assert duplicate.source_asset_id == original.source_asset_id
    assert duplicate.opacity == original.opacity
    assert duplicate.visible == original.visible
    assert duplicate.blend_mode is original.blend_mode
    assert duplicate.mask == original.mask


def test_move_layer_command_preserves_layer_identities() -> None:
    first = _layer()
    second = _layer()
    third = _layer()
    editor = _editor(LayerStack().add(first).add(second).add(third))
    result = editor.execute(ReorderLayerCommand(2, 0), {"operation": "move_layer"})
    assert result.layer_stack.layers == (third, first, second)


@pytest.mark.parametrize(
    ("command_factory", "value"),
    [
        (SetLayerVisibilityCommand, True),
        (SetLayerVisibilityCommand, False),
        (SetLayerOpacityCommand, 0.0),
        (SetLayerOpacityCommand, 1.0),
        (SetLayerBlendModeCommand, LayerBlendMode.MULTIPLY),
    ],
)
def test_layer_property_commands_accept_contract_boundaries(command_factory, value) -> None:
    layer = _layer()
    editor = _editor(LayerStack().add(layer))
    command = command_factory(layer.layer_id, value)
    result = editor.execute(command, {"operation": "layer_property"})
    changed = result.layer_stack.layers[0]
    if isinstance(value, bool):
        assert changed.visible is value
    elif isinstance(value, float):
        assert changed.opacity == value
    else:
        assert changed.blend_mode is value


@pytest.mark.parametrize("value", [True, False, math.nan, math.inf, -math.inf, -0.001, 1.001, "0.5"])
def test_opacity_command_rejects_invalid_values(value) -> None:
    with pytest.raises((TypeError, ValueError)):
        SetLayerOpacityCommand(uuid4(), value)


@pytest.mark.parametrize("value", [1, 0, "true", None])
def test_visibility_command_rejects_non_boolean_values(value) -> None:
    with pytest.raises(TypeError):
        SetLayerVisibilityCommand(uuid4(), value)


def test_failed_layer_command_does_not_create_revision() -> None:
    layer = _layer()
    editor = _editor(LayerStack().add(layer))
    before = editor.current_state.canonical_json
    before_count = editor.revision_count
    with pytest.raises(KeyError):
        editor.execute(RemoveLayerCommand(uuid4()), {"operation": "remove_layer"})
    assert editor.current_state.canonical_json == before
    assert editor.revision_count == before_count


def test_add_rejects_duplicate_identity_and_maximum_boundary() -> None:
    first = _layer()
    editor = _editor(LayerStack((first,), max_layers=1))
    with pytest.raises(ValueError, match="duplicate layer_id"):
        editor.execute(AddLayerCommand(first), {"operation": "add_layer"})
    assert editor.revision_count == 1
    with pytest.raises(ValueError, match="maximum layer count"):
        editor.execute(AddLayerCommand(_layer()), {"operation": "add_layer"})
    assert editor.revision_count == 1


@pytest.mark.parametrize("source, target", [(-1, 0), (0, 1), (1, 0), (0, -1)])
def test_move_rejects_out_of_range_indices_without_revision(source: int, target: int) -> None:
    layer = _layer()
    editor = _editor(LayerStack().add(layer))
    with pytest.raises(IndexError):
        editor.execute(ReorderLayerCommand(source, target), {"operation": "move_layer"})
    assert editor.revision_count == 1


def test_duplicate_rejects_existing_identity_without_revision() -> None:
    first = _layer()
    second = _layer()
    editor = _editor(LayerStack().add(first).add(second))
    with pytest.raises(ValueError, match="duplicate layer_id"):
        editor.execute(DuplicateLayerCommand(first.layer_id, second.layer_id), {"operation": "duplicate_layer"})
    assert editor.revision_count == 1


def test_layer_editing_is_canonically_deterministic() -> None:
    first = _layer()
    editor_a = _editor(LayerStack().add(first))
    editor_b = ProjectEditor.from_canonical_json(editor_a.canonical_json)
    command = SetLayerOpacityCommand(first.layer_id, 0.5)
    result_a = editor_a.execute(command, {"operation": "set_opacity"})
    result_b = editor_b.execute(command, {"operation": "set_opacity"})
    assert result_a.canonical_json == result_b.canonical_json
    assert editor_a.canonical_json == editor_b.canonical_json
