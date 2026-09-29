from __future__ import annotations

import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

MAX_COORDINATE = 320.0
MIN_SCALE = 0.01
MAX_SCALE = 64.0


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _bounded(value: float, lower: float, upper: float, name: str) -> float:
    value = _finite(value, name)
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be between {lower:g} and {upper:g}")
    return value


def _coordinate(value: float, name: str) -> float:
    return _bounded(value, -MAX_COORDINATE, MAX_COORDINATE, name)


def _crop(value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, tuple)
        or len(value) != 4
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise TypeError("crop must be a four-integer tuple")
    x, y, width, height = value
    if not 0 <= x <= 320 or not 0 <= y <= 320:
        raise ValueError("crop origin must be within the 320x320 canvas")
    if width < 1 or height < 1 or x + width > 320 or y + height > 320:
        raise ValueError("crop rectangle must fit within the 320x320 canvas")
    return value


@dataclass(frozen=True, slots=True)
class TransformState:
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    crop: tuple[int, int, int, int] = (0, 0, 320, 320)

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _coordinate(self.x, "x"))
        object.__setattr__(self, "y", _coordinate(self.y, "y"))
        object.__setattr__(self, "scale", _bounded(self.scale, MIN_SCALE, MAX_SCALE, "scale"))
        object.__setattr__(self, "crop", _crop(self.crop))

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"x": self.x, "y": self.y, "scale": self.scale, "crop": self.crop})

    @property
    def canonical_json(self) -> str:
        return json.dumps({"crop": list(self.crop), "scale": self.scale, "x": self.x, "y": self.y}, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class CropCommand:
    x: int
    y: int
    width: int
    height: int
    operation: str = "crop"

    def __post_init__(self) -> None:
        _crop((self.x, self.y, self.width, self.height))

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"x": self.x, "y": self.y, "width": self.width, "height": self.height})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        current = _current_transform(state)
        transform = TransformState(current.x, current.y, current.scale, (self.x, self.y, self.width, self.height))
        return _apply(self, state, transform)


@dataclass(frozen=True, slots=True)
class ScaleCommand:
    scale: float
    operation: str = "scale"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scale", _bounded(self.scale, MIN_SCALE, MAX_SCALE, "scale"))

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"scale": self.scale})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        current = _current_transform(state)
        transform = TransformState(current.x, current.y, self.scale, current.crop)
        return _apply(self, state, transform)


@dataclass(frozen=True, slots=True)
class TranslateCommand:
    dx: float
    dy: float
    operation: str = "translate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "dx", _coordinate(self.dx, "dx"))
        object.__setattr__(self, "dy", _coordinate(self.dy, "dy"))

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"dx": self.dx, "dy": self.dy})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        current = _current_transform(state)
        transform = TransformState(current.x + self.dx, current.y + self.dy, current.scale, current.crop)
        return _apply(self, state, transform)


def _current_transform(state: Any) -> TransformState:
    if isinstance(state, TransformState):
        return state
    from .project import ProjectState

    if not isinstance(state, ProjectState):
        raise TypeError("state must be a TransformState or ProjectState")
    return state.transform


def _apply(command: Any, state: Any, transform: TransformState) -> Any:
    if isinstance(state, TransformState):
        return transform
    from .project import ProjectState

    if not isinstance(state, ProjectState):
        raise TypeError("state must be a TransformState or ProjectState")
    return ProjectState(state.project_id, state.revision + 1, state.design, state.processing, state.metadata, transform=transform)


def _command_json(operation: str, metadata: MappingProxyType) -> str:
    return json.dumps({**dict(metadata), "operation": operation}, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
