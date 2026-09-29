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
        if (
            not isinstance(self.crop, tuple)
            or len(self.crop) != 4
            or any(isinstance(value, bool) or not isinstance(value, int) for value in self.crop)
        ):
            raise TypeError("crop must be a four-integer tuple")
        x, y, width, height = self.crop
        if not 0 <= x <= 320 or not 0 <= y <= 320:
            raise ValueError("crop origin must be within the 320x320 canvas")
        if width < 1 or height < 1 or x + width > 320 or y + height > 320:
            raise ValueError("crop rectangle must fit within the 320x320 canvas")

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType(
            {"x": self.x, "y": self.y, "scale": self.scale, "crop": self.crop}
        )

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            {"crop": list(self.crop), "scale": self.scale, "x": self.x, "y": self.y},
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )


class CropCommand:
    operation = "crop"

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self._state = TransformState(crop=(x, y, width, height))

    @property
    def metadata(self) -> MappingProxyType:
        x, y, width, height = self._state.crop
        return MappingProxyType({"x": x, "y": y, "width": width, "height": height})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        if isinstance(state, TransformState):
            return TransformState(state.x, state.y, state.scale, self._state.crop)
        return _apply_project_state(self, state, TransformState(state.x, state.y, state.scale, self._state.crop))


class ScaleCommand:
    operation = "scale"

    def __init__(self, scale: float) -> None:
        self._scale = _bounded(scale, MIN_SCALE, MAX_SCALE, "scale")

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"scale": self._scale})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        if isinstance(state, TransformState):
            return TransformState(state.x, state.y, self._scale, state.crop)
        return _apply_project_state(self, state, TransformState(state.x, state.y, self._scale, state.crop))


class TranslateCommand:
    operation = "translate"

    def __init__(self, dx: float, dy: float) -> None:
        self._dx = _coordinate(dx, "dx")
        self._dy = _coordinate(dy, "dy")

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({"dx": self._dx, "dy": self._dy})

    @property
    def canonical_json(self) -> str:
        return _command_json(self.operation, self.metadata)

    def apply(self, state: Any) -> Any:
        if isinstance(state, TransformState):
            return TransformState(
                state.x + self._dx,
                state.y + self._dy,
                state.scale,
                state.crop,
            )
        return _apply_project_state(
            self,
            state,
            TransformState(
                state.transform.x + self._dx,
                state.transform.y + self._dy,
                state.transform.scale,
                state.transform.crop,
            ),
        )


def _command_json(operation: str, metadata: MappingProxyType) -> str:
    return json.dumps(
        {**dict(metadata), "operation": operation},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _apply_project_state(command: Any, state: Any, transform: TransformState) -> Any:
    from .project import ProjectState

    if not isinstance(state, ProjectState):
        raise TypeError("state must be a TransformState or ProjectState")
    return ProjectState(
        state.project_id,
        state.revision + 1,
        state.design,
        state.processing,
        state.metadata,
        transform=transform,
    )
