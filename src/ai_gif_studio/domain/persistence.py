from __future__ import annotations

import json
from typing import Any

from .revisions import Revision, RevisionGraph, RevisionGraphError

SCHEMA_VERSION = 1
DEFAULT_MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_REVISIONS = 10_000

_TOP_LEVEL_KEYS = frozenset(
    {"schema_version", "root_revision_id", "current_revision_id", "revisions"}
)


class PersistenceValidationError(RevisionGraphError, ValueError):
    """Raised when a persisted revision graph violates the persistence contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PersistenceValidationError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise PersistenceValidationError(f"non-finite JSON number is not allowed: {value}")


def _validate_limit(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _dump(payload: Any) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise PersistenceValidationError("payload is not canonically JSON-serializable") from exc


class RevisionGraphPersistence:
    """Pure canonical serialization boundary for a RevisionGraph."""

    @staticmethod
    def encode(
        graph: RevisionGraph,
        *,
        max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
        max_revisions: int = DEFAULT_MAX_REVISIONS,
    ) -> str:
        if not isinstance(graph, RevisionGraph):
            raise TypeError("graph must be a RevisionGraph")
        _validate_limit(max_document_bytes, "max_document_bytes")
        _validate_limit(max_revisions, "max_revisions")
        try:
            graph.validate()
            revisions = graph.revisions
            root = graph.root
            current = graph.current
        except RevisionGraphError as exc:
            raise PersistenceValidationError("graph is invalid") from exc
        if len(revisions) > max_revisions:
            raise PersistenceValidationError("revision count exceeds persistence limit")

        payload = {
            "schema_version": SCHEMA_VERSION,
            "root_revision_id": root.revision_id,
            "current_revision_id": current.revision_id,
            "revisions": [
                json.loads(revision.canonical_json)
                for revision in sorted(revisions, key=lambda item: item.revision_id)
            ],
        }
        document = _dump(payload)
        if len(document.encode("utf-8")) > max_document_bytes:
            raise PersistenceValidationError("persisted document exceeds byte limit")
        return document

    @staticmethod
    def decode(
        document: str,
        *,
        max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
        max_revisions: int = DEFAULT_MAX_REVISIONS,
    ) -> RevisionGraph:
        if not isinstance(document, str):
            raise TypeError("document must be a string")
        _validate_limit(max_document_bytes, "max_document_bytes")
        _validate_limit(max_revisions, "max_revisions")
        if len(document.encode("utf-8")) > max_document_bytes:
            raise PersistenceValidationError("persisted document exceeds byte limit")
        try:
            payload = json.loads(
                document,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_non_finite,
            )
        except PersistenceValidationError:
            raise
        except (json.JSONDecodeError, RecursionError, ValueError, TypeError) as exc:
            raise PersistenceValidationError("invalid persisted JSON document") from exc

        if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
            raise PersistenceValidationError("persisted document has invalid top-level fields")
        if payload["schema_version"] != SCHEMA_VERSION or isinstance(
            payload["schema_version"], bool
        ):
            raise PersistenceValidationError("unsupported persistence schema version")

        revisions_payload = payload["revisions"]
        if not isinstance(revisions_payload, list) or not revisions_payload:
            raise PersistenceValidationError("persisted revisions must be a non-empty array")
        if len(revisions_payload) > max_revisions:
            raise PersistenceValidationError("revision count exceeds persistence limit")

        try:
            revisions = []
            for revision_payload in revisions_payload:
                if not isinstance(revision_payload, dict):
                    raise PersistenceValidationError("revision entries must be JSON objects")
                revision_json = _dump(revision_payload)
                revisions.append(Revision.from_canonical_json(revision_json))
        except (RevisionGraphError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PersistenceValidationError("persisted revision is invalid") from exc

        by_id = {revision.revision_id: revision for revision in revisions}
        if len(by_id) != len(revisions):
            raise PersistenceValidationError("persisted revisions contain duplicate identities")

        root_id = payload["root_revision_id"]
        current_id = payload["current_revision_id"]
        if not isinstance(root_id, str) or not isinstance(current_id, str):
            raise PersistenceValidationError("root/current revision ids must be strings")
        if root_id not in by_id or current_id not in by_id:
            raise PersistenceValidationError("root/current revision id is missing")

        roots = [revision for revision in revisions if revision.parent_id is None]
        if len(roots) != 1 or roots[0].revision_id != root_id:
            raise PersistenceValidationError("persisted graph must contain exactly one declared root")

        try:
            graph = RevisionGraph(roots[0], max_nodes=max_revisions)
            for revision in sorted(revisions, key=lambda item: item.revision_id):
                if revision.revision_id != root_id:
                    graph.add(revision)
            graph.checkout(current_id)
            graph.validate()
        except (RevisionGraphError, ValueError, TypeError) as exc:
            raise PersistenceValidationError("persisted graph structure is invalid") from exc

        try:
            canonical = RevisionGraphPersistence.encode(
                graph,
                max_document_bytes=max_document_bytes,
                max_revisions=max_revisions,
            )
        except PersistenceValidationError:
            raise
        if canonical != document:
            raise PersistenceValidationError("persisted document is not canonical")
        return graph
