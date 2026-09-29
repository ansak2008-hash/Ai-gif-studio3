from __future__ import annotations

from uuid import uuid4

import pytest

from ai_gif_studio.domain.commands import (
    CommandHistory,
    CommandHistoryError,
    ReplaceDesignSpecCommand,
    ReplaceProcessingSettingsCommand,
)
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings

pytestmark = pytest.mark.unit


def _state() -> ProjectState:
    return ProjectState(uuid4(), 0, DesignSpec(), ProcessingSettings(), {})


def test_commands_produce_new_immutable_states() -> None:
    state = _state()
    design = DesignSpec(
        background={"mode": "solid", "color": "#222222"},
    )
    updated = ReplaceDesignSpecCommand(design).apply(state)

    assert updated is not state
    assert updated.revision == 1
    assert updated.design.background["color"] == "#222222"
    assert state.revision == 0


def test_processing_command_preserves_design_and_increments_revision() -> None:
    state = _state()
    settings = ProcessingSettings(fps=24)
    updated = ReplaceProcessingSettingsCommand(settings).apply(state)

    assert updated.revision == 1
    assert updated.design == state.design
    assert updated.processing.fps == 24


def test_command_history_undo_redo_and_branch_invalidation() -> None:
    history = CommandHistory(_state())
    updated = history.execute(
        ReplaceDesignSpecCommand(
            DesignSpec(background={"mode": "solid", "color": "#222222"})
        )
    )
    assert history.current is updated
    assert history.can_undo is True
    assert history.can_redo is False

    undone = history.undo()
    assert undone.revision == 0
    assert history.can_redo is True

    redone = history.redo()
    assert redone.canonical_json == updated.canonical_json
    assert history.can_undo is True

    history.undo()
    history.execute(ReplaceProcessingSettingsCommand(ProcessingSettings(fps=12)))
    assert history.can_redo is False


def test_empty_history_operations_raise_typed_error() -> None:
    history = CommandHistory(_state())
    with pytest.raises(CommandHistoryError, match="nothing to undo"):
        history.undo()
    with pytest.raises(CommandHistoryError, match="nothing to redo"):
        history.redo()


def test_command_configuration_is_frozen() -> None:
    command = ReplaceProcessingSettingsCommand(ProcessingSettings())
    with pytest.raises((AttributeError, TypeError)):
        command.processing = ProcessingSettings(fps=24)  # type: ignore[misc]
