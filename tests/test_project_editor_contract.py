from __future__ import annotations

from uuid import uuid4

import pytest

from ai_gif_studio.domain.commands import ReplaceDesignSpecCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.services.project_editor import ProjectEditor

pytestmark = pytest.mark.unit


def _state() -> ProjectState:
    return ProjectState(
        uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {"fixture": "phase-6-1"},
    )


def _design(color: str) -> DesignSpec:
    return DesignSpec(background={"mode": "solid", "color": color})


def test_create_starts_at_single_root_revision() -> None:
    editor = ProjectEditor.create(_state())
    assert editor.revision_count == 1
    assert editor.current_state.revision == 0
    assert editor.current_revision.parent_id is None


def test_execute_creates_one_child_and_preserves_parent() -> None:
    editor = ProjectEditor.create(_state())
    parent_id = editor.current_revision_id
    command = ReplaceDesignSpecCommand(_design("#222222"))

    current = editor.execute(command, {"operation": "change_background"})

    assert editor.revision_count == 2
    assert current.revision == 1
    assert editor.current_revision.parent_id == parent_id
    assert editor.get_revision(parent_id).state.revision == 0


def test_failed_execute_does_not_mutate_graph() -> None:
    editor = ProjectEditor.create(_state())
    before = editor.canonical_json

    with pytest.raises(TypeError):
        editor.execute(object(), {"operation": "invalid"})

    assert editor.canonical_json == before
    assert editor.revision_count == 1


def test_checkout_restores_existing_revision_without_deletion() -> None:
    editor = ProjectEditor.create(_state())
    root_id = editor.current_revision_id
    editor.execute(
        ReplaceDesignSpecCommand(_design("#222222")),
        {"operation": "change_background"},
    )
    child_id = editor.current_revision_id

    restored = editor.checkout(root_id)

    assert restored.revision == 0
    assert editor.current_revision_id == root_id
    assert editor.revision_count == 2
    assert editor.get_revision(child_id).state.revision == 1


def test_canonical_round_trip_preserves_graph_and_current_revision() -> None:
    editor = ProjectEditor.create(_state())
    editor.execute(
        ReplaceDesignSpecCommand(_design("#222222")),
        {"operation": "change_background"},
    )
    document = editor.canonical_json

    restored = ProjectEditor.from_canonical_json(document)

    assert restored.canonical_json == document
    assert restored.current_revision_id == editor.current_revision_id
    assert restored.current_state == editor.current_state


def test_branching_after_checkout_preserves_both_children() -> None:
    editor = ProjectEditor.create(_state())
    root_id = editor.current_revision_id
    first = editor.execute(
        ReplaceDesignSpecCommand(_design("#222222")),
        {"operation": "dark_background"},
    )
    first_id = editor.current_revision_id
    editor.checkout(root_id)
    second = editor.execute(
        ReplaceDesignSpecCommand(_design("#333333")),
        {"operation": "alternate_background"},
    )

    assert second.revision == 1
    assert first.revision == 1
    assert editor.get_revision(first_id).parent_id == root_id
    assert editor.get_revision(editor.current_revision_id).parent_id == root_id
    assert first_id != editor.current_revision_id
    assert editor.revision_count == 3


def test_invalid_metadata_does_not_mutate_graph() -> None:
    editor = ProjectEditor.create(_state())
    before = editor.canonical_json

    with pytest.raises(TypeError):
        editor.execute(
            ReplaceDesignSpecCommand(_design("#222222")),
            {"operation": object()},
        )

    assert editor.canonical_json == before
    assert editor.revision_count == 1


def test_deeply_nested_metadata_fails_as_contract_error() -> None:
    editor = ProjectEditor.create(_state())
    nested: dict[str, object] = {}
    current = nested
    for _ in range(2000):
        child: dict[str, object] = {}
        current["x"] = child
        current = child

    with pytest.raises(TypeError, match="JSON-compatible"):
        editor.execute(
            ReplaceDesignSpecCommand(_design("#222222")),
            nested,
        )

    assert editor.revision_count == 1


def test_deeply_nested_canonical_revision_fails_as_validation_error() -> None:
    nested_json = "{" + '"x":{' * 2000 + "null" + "}" * 2000 + "}"
    payload = (
        '{"command_metadata":'
        + nested_json
        + ',"parent_id":null,"revision_id":"'
        + "0" * 64
        + '","state":'
        + _state().canonical_json.__repr__()
        + "}"
    )

    from ai_gif_studio.domain.revisions import RevisionValidationError

    with pytest.raises(RevisionValidationError, match="invalid canonical revision JSON"):
        from ai_gif_studio.domain.revisions import Revision

        Revision.from_canonical_json(payload)
