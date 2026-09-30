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


def test_create_starts_at_single_root_revision() -> None:
    editor = ProjectEditor.create(_state())
    assert editor.revision_count == 1
    assert editor.current_state.revision == 0
    assert editor.current_revision.parent_id is None


def test_execute_creates_one_child_and_preserves_parent() -> None:
    editor = ProjectEditor.create(_state())
    parent_id = editor.current_revision_id
    command = ReplaceDesignSpecCommand(DesignSpec(canvas_width=640, canvas_height=360))

    current = editor.execute(command, {"operation": "resize_canvas"})

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
        ReplaceDesignSpecCommand(DesignSpec(canvas_width=640, canvas_height=360)),
        {"operation": "resize"},
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
        ReplaceDesignSpecCommand(DesignSpec(canvas_width=640, canvas_height=360)),
        {"operation": "resize"},
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
        ReplaceDesignSpecCommand(DesignSpec(canvas_width=640, canvas_height=360)),
        {"operation": "wide"},
    )
    first_id = editor.current_revision_id
    editor.checkout(root_id)
    second = editor.execute(
        ReplaceDesignSpecCommand(DesignSpec(canvas_width=360, canvas_height=640)),
        {"operation": "tall"},
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
            ReplaceDesignSpecCommand(DesignSpec(canvas_width=640, canvas_height=360)),
            {"operation": object()},
        )

    assert editor.canonical_json == before
    assert editor.revision_count == 1
