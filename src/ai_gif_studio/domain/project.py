from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .specs import DesignSpec, ProcessingSettings


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _load_canonical_json(value: str) -> Any:
    return json.loads(value, object_pairs_hook=_reject_duplicate_keys)


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

        payload = {
            "project_id": str(project_id),
            "revision": revision,
            "design": design.model_dump(mode="json"),
            "processing": processing.model_dump(mode="json"),
            "metadata": metadata,
        }
        try:
            canonical = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise TypeError("metadata must be JSON-compatible") from exc
        object.__setattr__(self, "_canonical_json", canonical)

    @classmethod
    def from_canonical_json(cls, value: str) -> ProjectState:
        if not isinstance(value, str):
            raise TypeError("canonical project state must be a string")
        try:
            payload = _load_canonical_json(value)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid canonical project state JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("canonical project state must be a JSON object")
        try:
            project_id = UUID(str(payload["project_id"]))
            revision = payload["revision"]
            design = DesignSpec.model_validate(payload["design"])
            processing = ProcessingSettings.model_validate(payload["processing"])
            metadata = payload["metadata"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid canonical project state payload") from exc
        state = cls(project_id, revision, design, processing, metadata)
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
