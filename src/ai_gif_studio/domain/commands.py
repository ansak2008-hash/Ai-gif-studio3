from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .layer_state import LayerStack
from .project import ProjectState
from .specs import DesignSpec, ProcessingSettings


class CommandHistoryError(RuntimeError):
    """Raised when an undo/redo operation cannot be performed."""


@runtime_checkable
class ProjectCommand(Protocol):
    def apply(self, state: ProjectState) -> ProjectState: ...


@dataclass(frozen=True, slots=True)
class ReplaceDesignSpecCommand:
    design: DesignSpec

    def __post_init__(self) -> None:
        if not isinstance(self.design, DesignSpec):
            raise TypeError("design must be a DesignSpec")

    def apply(self, state: ProjectState) -> ProjectState:
        if not isinstance(state, ProjectState):
            raise TypeError("state must be a ProjectState")
        return ProjectState(
            state.project_id,
            state.revision + 1,
            self.design,
            state.processing,
            state.metadata,
            transform=state.transform,
            layer_stack=state.layer_stack,
        )


@dataclass(frozen=True, slots=True)
class ReplaceProcessingSettingsCommand:
    processing: ProcessingSettings

    def __post_init__(self) -> None:
        if not isinstance(self.processing, ProcessingSettings):
            raise TypeError("processing must be a ProcessingSettings")

    def apply(self, state: ProjectState) -> ProjectState:
        if not isinstance(state, ProjectState):
            raise TypeError("state must be a ProjectState")
        return ProjectState(
            state.project_id,
            state.revision + 1,
            state.design,
            self.processing,
            state.metadata,
            transform=state.transform,
        )


@dataclass(frozen=True, slots=True)
class ReplaceLayerStackCommand:
    layer_stack: LayerStack

    def __post_init__(self) -> None:
        if not isinstance(self.layer_stack, LayerStack):
            raise TypeError("layer_stack must be a LayerStack")

    def apply(self, state: ProjectState) -> ProjectState:
        if not isinstance(state, ProjectState):
            raise TypeError("state must be a ProjectState")
        return ProjectState(
            state.project_id,
            state.revision + 1,
            state.design,
            state.processing,
            state.metadata,
            transform=state.transform,
            layer_stack=self.layer_stack,
        )


class CommandHistory:
    """Process-local navigation over immutable ProjectState snapshots."""

    def __init__(self, initial: ProjectState) -> None:
        if not isinstance(initial, ProjectState):
            raise TypeError("initial must be a ProjectState")
        self._current = initial
        self._undo: list[ProjectState] = []
        self._redo: list[ProjectState] = []

    @property
    def current(self) -> ProjectState:
        return self._current

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def execute(self, command: ProjectCommand) -> ProjectState:
        if not isinstance(command, ProjectCommand):
            raise TypeError("command must implement ProjectCommand")
        next_state = command.apply(self._current)
        if not isinstance(next_state, ProjectState):
            raise TypeError("command must return a ProjectState")
        if next_state is self._current:
            raise ValueError("command must return a new ProjectState")
        if next_state.revision != self._current.revision + 1:
            raise ValueError("command must increment revision exactly once")
        self._undo.append(self._current)
        self._current = next_state
        self._redo.clear()
        return self._current

    def undo(self) -> ProjectState:
        if not self._undo:
            raise CommandHistoryError("nothing to undo")
        self._redo.append(self._current)
        self._current = self._undo.pop()
        return self._current

    def redo(self) -> ProjectState:
        if not self._redo:
            raise CommandHistoryError("nothing to redo")
        self._undo.append(self._current)
        self._current = self._redo.pop()
        return self._current
