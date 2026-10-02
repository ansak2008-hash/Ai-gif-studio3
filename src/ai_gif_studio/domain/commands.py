from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from .layer_state import LayerBlendMode, LayerStack, LayerState
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
            layer_stack=state.layer_stack,
        )


def _require_project_state(state: ProjectState) -> ProjectState:
    if not isinstance(state, ProjectState):
        raise TypeError("state must be a ProjectState")
    return state


def _replace_layer_stack(state: ProjectState, layer_stack: LayerStack) -> ProjectState:
    _require_project_state(state)
    return ProjectState(
        state.project_id,
        state.revision + 1,
        state.design,
        state.processing,
        state.metadata,
        transform=state.transform,
        layer_stack=layer_stack,
    )


@dataclass(frozen=True, slots=True)
class AddLayerCommand:
    layer: LayerState

    def __post_init__(self) -> None:
        if not isinstance(self.layer, LayerState):
            raise TypeError("layer must be a LayerState")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(state, state.layer_stack.add(self.layer))


@dataclass(frozen=True, slots=True)
class RemoveLayerCommand:
    layer_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID):
            raise TypeError("layer_id must be a UUID")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(state, state.layer_stack.remove(self.layer_id))


@dataclass(frozen=True, slots=True)
class ReorderLayerCommand:
    source: int
    target: int

    def __post_init__(self) -> None:
        if isinstance(self.source, bool) or not isinstance(self.source, int):
            raise TypeError("source must be an integer")
        if isinstance(self.target, bool) or not isinstance(self.target, int):
            raise TypeError("target must be an integer")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(state, state.layer_stack.move(self.source, self.target))


@dataclass(frozen=True, slots=True)
class DuplicateLayerCommand:
    layer_id: UUID
    new_layer_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID) or not isinstance(self.new_layer_id, UUID):
            raise TypeError("layer identifiers must be UUID values")
        if self.layer_id == self.new_layer_id:
            raise ValueError("new_layer_id must differ from layer_id")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        stack = state.layer_stack
        for layer in stack.layers:
            if layer.layer_id == self.layer_id:
                source = layer
                break
        else:
            raise KeyError(f"unknown layer_id: {self.layer_id}")
        if len(stack.layers) >= stack.max_layers:
            raise ValueError("maximum layer count reached")
        if self.new_layer_id in {layer.layer_id for layer in stack.layers}:
            raise ValueError("duplicate layer_id")
        duplicate = LayerState(
            self.new_layer_id,
            source.source_asset_id,
            source.opacity,
            source.visible,
            source.blend_mode,
            source.mask,
        )
        index = stack.layers.index(source)
        layers = list(stack.layers)
        layers.insert(index + 1, duplicate)
        return _replace_layer_stack(
            state,
            LayerStack(tuple(layers), max_layers=stack.max_layers),
        )


@dataclass(frozen=True, slots=True)
class SetLayerVisibilityCommand:
    layer_id: UUID
    visible: bool

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID):
            raise TypeError("layer_id must be a UUID")
        if not isinstance(self.visible, bool):
            raise TypeError("visible must be a boolean")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(
            state,
            state.layer_stack.set_visibility(self.layer_id, self.visible),
        )


@dataclass(frozen=True, slots=True)
class SetLayerOpacityCommand:
    layer_id: UUID
    opacity: float

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID):
            raise TypeError("layer_id must be a UUID")
        if isinstance(self.opacity, bool) or not isinstance(self.opacity, int | float):
            raise TypeError("opacity must be numeric")
        normalized = float(self.opacity)
        if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
            raise ValueError("opacity must be finite and between 0 and 1")
        object.__setattr__(self, "opacity", normalized)

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(
            state,
            state.layer_stack.set_opacity(self.layer_id, self.opacity),
        )


@dataclass(frozen=True, slots=True)
class SetLayerBlendModeCommand:
    layer_id: UUID
    blend_mode: LayerBlendMode

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID):
            raise TypeError("layer_id must be a UUID")
        if not isinstance(self.blend_mode, LayerBlendMode):
            raise TypeError("blend_mode must be a LayerBlendMode")

    def apply(self, state: ProjectState) -> ProjectState:
        _require_project_state(state)
        return _replace_layer_stack(
            state,
            state.layer_stack.set_blend_mode(self.layer_id, self.blend_mode),
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
