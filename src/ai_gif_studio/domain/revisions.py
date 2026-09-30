from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any

from .canonical_validation import validate_mapping
from .project import ProjectState


class RevisionGraphError(RuntimeError):
    """Base error for revision graph contract violations."""


class RevisionValidationError(RevisionGraphError, ValueError):
    """Raised when a revision or revision identifier is invalid."""


class RevisionNotFoundError(RevisionGraphError, KeyError):
    """Raised when a requested revision does not exist."""


class RevisionLimitError(RevisionGraphError):
    """Raised when the graph node bound would be exceeded."""


def _canonical_metadata(metadata: Mapping[str, Any]) -> str:
    if not isinstance(metadata, Mapping):
        raise TypeError("command_metadata must be a mapping")
    validate_mapping(metadata, context="Revision.command_metadata")
    try:
        return json.dumps(
            dict(metadata),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise TypeError("command_metadata must be JSON-compatible") from exc


def _validate_revision_id(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("revision_id must be a string")
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise RevisionValidationError("revision_id must be a lowercase SHA-256 hex digest")


def _revision_identity(
    state: ProjectState,
    parent_id: str | None,
    command_metadata: str,
) -> str:
    envelope = {
        "parent_id": parent_id,
        "state": state.canonical_json,
        "command_metadata": json.loads(command_metadata),
    }
    validate_mapping(envelope, context="Revision.identity")
    canonical = json.dumps(
        envelope,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Revision:
    """Immutable content-addressed revision node."""

    revision_id: str
    parent_id: str | None
    state: ProjectState
    command_metadata: str

    @classmethod
    def create(
        cls,
        state: ProjectState,
        parent_id: str | None,
        command_metadata: Mapping[str, Any],
    ) -> Revision:
        if not isinstance(state, ProjectState):
            raise TypeError("state must be a ProjectState")
        if parent_id is not None:
            _validate_revision_id(parent_id)
        metadata = _canonical_metadata(command_metadata)
        revision_id = _revision_identity(state, parent_id, metadata)
        return cls(revision_id, parent_id, state, metadata)

    def __post_init__(self) -> None:
        _validate_revision_id(self.revision_id)
        if self.parent_id is not None:
            _validate_revision_id(self.parent_id)
        if not isinstance(self.state, ProjectState):
            raise TypeError("state must be a ProjectState")
        metadata = json.loads(self.command_metadata)
        _canonical_metadata(metadata)
        expected_id = _revision_identity(
            self.state,
            self.parent_id,
            self.command_metadata,
        )
        if expected_id != self.revision_id:
            raise RevisionValidationError("revision identity does not match revision content")

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            {
                "revision_id": self.revision_id,
                "parent_id": self.parent_id,
                "state": self.state.canonical_json,
                "command_metadata": json.loads(self.command_metadata),
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, value: str) -> Revision:
        if not isinstance(value, str):
            raise TypeError("revision JSON must be a string")
        try:
            value.encode("utf-8", "strict")
            payload = json.loads(value)
            if not isinstance(payload, dict):
                raise ValueError("revision payload must be an object")
            validate_mapping(payload, context="Revision")
            state = ProjectState.from_canonical_json(payload["state"])
            metadata = payload["command_metadata"]
            revision = cls.create(state, payload["parent_id"], metadata)
            if revision.revision_id != payload["revision_id"]:
                raise RevisionValidationError("revision identity mismatch")
            if revision.canonical_json != value:
                raise RevisionValidationError("revision JSON is not normalized")
            return revision
        except RevisionGraphError:
            raise
        except (UnicodeEncodeError, KeyError, TypeError, ValueError, RecursionError, json.JSONDecodeError) as exc:
            raise RevisionValidationError("invalid canonical revision JSON") from exc


class RevisionGraph:
    """Bounded mutable index over immutable Revision nodes."""

    def __init__(self, root: Revision, *, max_nodes: int = 10_000) -> None:
        if not isinstance(root, Revision):
            raise TypeError("root must be a Revision")
        if root.parent_id is not None:
            raise RevisionValidationError("root revision must not have a parent")
        if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 1:
            raise ValueError("max_nodes must be a positive integer")
        self._max_nodes = max_nodes
        self._nodes: dict[str, Revision] = {root.revision_id: root}
        self._current_id = root.revision_id
        self._lock = RLock()

    @property
    def current(self) -> Revision:
        with self._lock:
            return self._nodes[self._current_id]

    @property
    def root(self) -> Revision:
        with self._lock:
            return next(revision for revision in self._nodes.values() if revision.parent_id is None)

    @property
    def revisions(self) -> tuple[Revision, ...]:
        with self._lock:
            return tuple(self._nodes.values())

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._nodes)

    def get(self, revision_id: str) -> Revision:
        _validate_revision_id(revision_id)
        with self._lock:
            try:
                return self._nodes[revision_id]
            except KeyError as exc:
                raise RevisionNotFoundError(revision_id) from exc

    def add(self, revision: Revision) -> Revision:
        if not isinstance(revision, Revision):
            raise TypeError("revision must be a Revision")
        with self._lock:
            existing = self._nodes.get(revision.revision_id)
            if existing is not None:
                if existing == revision:
                    raise RevisionValidationError("duplicate revision")
                raise RevisionValidationError("revision id collision")
            if revision.parent_id is None or revision.parent_id not in self._nodes:
                raise RevisionValidationError("revision parent does not exist")
            if len(self._nodes) >= self._max_nodes:
                raise RevisionLimitError("revision graph node limit exceeded")
            self._nodes[revision.revision_id] = revision
            return revision

    def checkout(self, revision_id: str) -> Revision:
        revision = self.get(revision_id)
        with self._lock:
            self._current_id = revision.revision_id
            return revision

    def is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        _validate_revision_id(ancestor_id)
        _validate_revision_id(descendant_id)
        with self._lock:
            if ancestor_id == descendant_id:
                return True
            current = self._nodes.get(descendant_id)
            if current is None:
                raise RevisionNotFoundError(descendant_id)
            while current.parent_id is not None:
                parent = self._nodes.get(current.parent_id)
                if parent is None:
                    raise RevisionValidationError("graph contains an orphaned parent")
                if parent.revision_id == ancestor_id:
                    return True
                current = parent
            return False

    def ancestry(self, revision_id: str) -> tuple[str, ...]:
        current = self.get(revision_id)
        with self._lock:
            result: list[str] = []
            while True:
                result.append(current.revision_id)
                if current.parent_id is None:
                    break
                parent = self._nodes.get(current.parent_id)
                if parent is None:
                    raise RevisionValidationError("graph contains an orphaned parent")
                current = parent
            return tuple(result)

    def validate(self) -> None:
        with self._lock:
            if len(self._nodes) > self._max_nodes:
                raise RevisionLimitError("revision graph node limit exceeded")
            if self._current_id not in self._nodes:
                raise RevisionValidationError("current revision is missing")
            for revision_id, revision in self._nodes.items():
                if revision_id != revision.revision_id:
                    raise RevisionValidationError("revision index key mismatch")
                if revision.parent_id is not None and revision.parent_id not in self._nodes:
                    raise RevisionValidationError("graph contains an orphaned parent")
                expected = Revision.create(
                    revision.state,
                    revision.parent_id,
                    json.loads(revision.command_metadata),
                )
                if expected.revision_id != revision.revision_id:
                    raise RevisionValidationError("graph contains corrupted revision identity")
