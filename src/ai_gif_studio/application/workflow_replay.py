from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ai_gif_studio.domain.canonical_validation import validate_mapping, validate_string
from ai_gif_studio.domain.commands import ProjectCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.services.project_editor import ProjectEditor

WORKFLOW_SCHEMA_VERSION = 1

_TOP_LEVEL_KEYS = frozenset({"contract_version", "id", "operations"})
_OPERATION_KEYS = frozenset({"capability_id", "capability_version", "metadata", "payload"})


class WorkflowReplayError(RuntimeError):
    """Raised when workflow replay fails at a specific operation."""

    def __init__(self, operation_index: int, committed_operations: int) -> None:
        super().__init__(f"workflow replay failed at operation {operation_index}")
        self.operation_index = operation_index
        self.committed_operations = committed_operations


def _validate_version(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _canonical_json(value: Any, *, context: str) -> str:
    try:
        validate_mapping(value, context=context)
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{context} is not canonically JSON-compatible") from exc


@dataclass(frozen=True, slots=True)
class WorkflowOperation:
    capability_id: str
    capability_version: int
    _payload_json: str
    _metadata_json: str

    def __init__(
        self,
        capability_id: str,
        capability_version: int,
        payload: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> None:
        validate_string(capability_id, context="capability_id")
        if not capability_id.strip():
            raise ValueError("capability_id must be a non-empty string")
        _validate_version(capability_version, "capability_version")
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "capability_version", capability_version)
        object.__setattr__(self, "_payload_json", _canonical_json(payload, context="payload"))
        object.__setattr__(self, "_metadata_json", _canonical_json(metadata, context="metadata"))

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)

    @property
    def metadata(self) -> dict[str, Any]:
        return json.loads(self._metadata_json)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            {
                "capability_id": self.capability_id,
                "capability_version": self.capability_version,
                "metadata": json.loads(self._metadata_json),
                "payload": json.loads(self._payload_json),
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True, slots=True)
class Workflow:
    id: str
    contract_version: int
    operations: tuple[WorkflowOperation, ...]

    def __post_init__(self) -> None:
        validate_string(self.id, context="id")
        if not self.id.strip():
            raise ValueError("id must be a non-empty identifier")
        _validate_version(self.contract_version, "contract_version")
        if self.contract_version != WORKFLOW_SCHEMA_VERSION:
            raise ValueError("unsupported workflow schema version")
        if not isinstance(self.operations, tuple):
            object.__setattr__(self, "operations", tuple(self.operations))
        if any(not isinstance(item, WorkflowOperation) for item in self.operations):
            raise TypeError("operations must contain WorkflowOperation objects")

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            {
                "contract_version": self.contract_version,
                "id": self.id,
                "operations": [
                    json.loads(operation.canonical_json) for operation in self.operations
                ],
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, document: str) -> Workflow:
        if not isinstance(document, str):
            raise TypeError("workflow JSON must be a string")
        try:
            payload = json.loads(
                document,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_non_finite,
            )
        except (json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise ValueError("invalid canonical workflow JSON") from exc
        if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
            raise ValueError("workflow JSON has invalid top-level fields")
        if payload["contract_version"] != WORKFLOW_SCHEMA_VERSION:
            raise ValueError("unsupported workflow schema version")
        operations_payload = payload["operations"]
        if not isinstance(operations_payload, list):
            raise ValueError("workflow operations must be an array")
        operations: list[WorkflowOperation] = []
        for item in operations_payload:
            if not isinstance(item, dict) or set(item) != _OPERATION_KEYS:
                raise ValueError("workflow operation has invalid fields")
            operations.append(
                WorkflowOperation(
                    item["capability_id"],
                    item["capability_version"],
                    item["payload"],
                    item["metadata"],
                )
            )
        workflow = cls(payload["id"], payload["contract_version"], tuple(operations))
        if workflow.canonical_json != document:
            raise ValueError("workflow JSON is not canonical")
        return workflow


@dataclass(frozen=True, slots=True)
class WorkflowReplayResult:
    final_state: ProjectState
    committed_operations: int


def replay_workflow(
    editor: ProjectEditor,
    workflow: Workflow,
    resolver: Callable[[WorkflowOperation], ProjectCommand],
) -> WorkflowReplayResult:
    if not isinstance(editor, ProjectEditor):
        raise TypeError("editor must be a ProjectEditor")
    if not isinstance(workflow, Workflow):
        raise TypeError("workflow must be a Workflow")
    if not callable(resolver):
        raise TypeError("resolver must be callable")
    committed = 0
    for index, operation in enumerate(workflow.operations):
        try:
            command = resolver(operation)
            if not isinstance(command, ProjectCommand):
                raise TypeError("resolver must return a ProjectCommand")
            editor.execute(command, operation.metadata)
        except Exception as exc:
            error = WorkflowReplayError(index, committed)
            raise error from exc
        committed += 1
    return WorkflowReplayResult(editor.current_state, committed)
