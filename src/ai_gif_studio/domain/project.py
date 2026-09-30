from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .canonical_validation import validate_mapping
from .layer_state import LayerStack
from .specs import DesignSpec, ProcessingSettings
from .transforms import TransformState


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


_MAX_CANONICAL_JSON_BYTES = 8 * 1024 * 1024
_MAX_CANONICAL_JSON_DEPTH = 128


def _validate_json_payload_bounds(value: str) -> None:
    if len(value.encode("utf-8")) > _MAX_CANONICAL_JSON_BYTES:
        raise ValueError("canonical project state exceeds the maximum JSON payload size")

    depth = 0
    in_string = False
    escaped = False
    for char in value:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > _MAX_CANONICAL_JSON_DEPTH:
                raise ValueError(
                    "canonical project state exceeds the maximum JSON nesting depth"
                )
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("invalid canonical project state JSON")


def _load_canonical_json(value: str) -> Any:
    _validate_json_payload_bounds(value)
    try:
        return json.loads(value, object_pairs_hook=_reject_duplicate_keys)
    except RecursionError as exc:
        raise ValueError("canonical project state exceeds the maximum JSON nesting depth") from exc


@dataclass(frozen=True, slots=True, init=False)
class ProjectState:
    """Immutable, detached project snapshot for the Phase 5 composition track."""

    _canonical_json: str

    def __init__(
        self,
        project_id: UUID,
        revision: int,
        design: DesignSpec,
        processing: ProcessingSettings,
        metadata: dict[str, Any],
        transform: TransformState | None = None,
        layer_stack: LayerStack | None = None,
    ) -> None:
        if not isinstance(project_id, UUID):
            raise TypeError("project_id must be a UUID")
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise TypeError("revision must be an integer")
        if revision < 0:
            raise ValueError("revision must be non-negative")
        if not isinstance(design, DesignSpec):
            raise TypeError("design must be a DesignSpec")
        if not isinstance(processing, ProcessingSettings):
            raise TypeError("processing must be a ProcessingSettings")
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary")
        validate_mapping(metadata, context="ProjectState.metadata")
        if transform is not None and not isinstance(transform, TransformState):
            raise TypeError("transform must be a TransformState or None")
        if layer_stack is not None and not isinstance(layer_stack, LayerStack):
            raise TypeError("layer_stack must be a LayerStack or None")

        payload = {
            "project_id": str(project_id),
            "revision": revision,
            "design": design.model_dump(mode="json"),
            "processing": processing.model_dump(mode="json"),
            "metadata": metadata,
        }
        if transform is not None and transform != TransformState():
            payload["transform"] = {"x": transform.x, "y": transform.y, "scale": transform.scale, "crop": list(transform.crop)}
            if transform.rotation != 0.0:
                payload["transform"]["rotation"] = transform.rotation
        if layer_stack is not None and layer_stack != LayerStack():
            payload["layer_stack"] = json.loads(layer_stack.canonical_json)
        validate_mapping(payload, context="ProjectState")
        try:
            canonical = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError, RecursionError) as exc:
            raise TypeError("metadata must be JSON-compatible") from exc
        if len(canonical.encode("utf-8")) > _MAX_CANONICAL_JSON_BYTES:
            raise ValueError("canonical project state exceeds the maximum JSON payload size")
        object.__setattr__(self, "_canonical_json", canonical)

    @classmethod
    def from_canonical_json(cls, value: str) -> ProjectState:
        if not isinstance(value, str):
            raise TypeError("canonical project state must be a string")
        try:
            value.encode("utf-8", "strict")
            payload = _load_canonical_json(value)
        except UnicodeEncodeError as exc:
            raise ValueError("invalid UTF-8 canonical project state") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid canonical project state JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("canonical project state must be a JSON object")
        try:
            validate_mapping(payload, context="loaded_project")
            project_id = UUID(str(payload["project_id"]))
            revision = payload["revision"]
            design = DesignSpec.model_validate(payload["design"])
            processing = ProcessingSettings.model_validate(payload["processing"])
            metadata = payload["metadata"]
            raw_transform = payload.get("transform")
            transform = None if raw_transform is None else TransformState(x=raw_transform["x"], y=raw_transform["y"], rotation=raw_transform.get("rotation", 0.0), scale=raw_transform["scale"], crop=tuple(raw_transform["crop"]))
            raw_layer_stack = payload.get("layer_stack")
            layer_stack = None if raw_layer_stack is None else LayerStack.from_canonical_json(json.dumps(raw_layer_stack, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid canonical project state payload") from exc
        state = cls(project_id, revision, design, processing, metadata, transform=transform, layer_stack=layer_stack)
        if state.canonical_json != value:
            raise ValueError("canonical project state is not normalized")
        return state

    @property
    def canonical_json(self) -> str:
        return self._canonical_json

    @property
    def project_id(self) -> UUID:
        return UUID(_load_canonical_json(self._canonical_json)["project_id"])

    @property
    def revision(self) -> int:
        return int(_load_canonical_json(self._canonical_json)["revision"])

    @property
    def design(self) -> DesignSpec:
        return DesignSpec.model_validate(_load_canonical_json(self._canonical_json)["design"])

    @property
    def processing(self) -> ProcessingSettings:
        return ProcessingSettings.model_validate(
            _load_canonical_json(self._canonical_json)["processing"]
        )

    @property
    def metadata(self) -> dict[str, Any]:
        return _load_canonical_json(self._canonical_json)["metadata"]

    @property
    def layer_stack(self) -> LayerStack:
        payload = _load_canonical_json(self._canonical_json)
        raw = payload.get("layer_stack")
        if raw is None:
            return LayerStack()
        return LayerStack.from_canonical_json(
            json.dumps(raw, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
        )

    @property
    def transform(self) -> TransformState:
        payload = _load_canonical_json(self._canonical_json)
        raw = payload.get("transform")
        if raw is None:
            return TransformState()
        return TransformState(x=raw["x"], y=raw["y"], rotation=raw.get("rotation", 0.0), scale=raw["scale"], crop=tuple(raw["crop"]))
