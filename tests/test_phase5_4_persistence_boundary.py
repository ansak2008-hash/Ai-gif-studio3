from __future__ import annotations

import json

import pytest

from ai_gif_studio.domain.persistence import (
    DEFAULT_MAX_DOCUMENT_BYTES,
    DEFAULT_MAX_REVISIONS,
    PersistenceValidationError,
    RevisionGraphPersistence,
)
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.revisions import Revision, RevisionGraph
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings


def _graph() -> RevisionGraph:
    root = Revision.create(
        ProjectState(__import__("uuid").uuid4(), 0, DesignSpec(), ProcessingSettings(), {}),
        None,
        {"command": "root"},
    )
    graph = RevisionGraph(root)
    child = Revision.create(
        ProjectState(root.state.project_id, 1, DesignSpec(), root.state.processing, {"marker": "child"}),
        root.revision_id,
        {"command": "child"},
    )
    graph.add(child)
    graph.checkout(child.revision_id)
    return graph


def test_canonical_document_is_deterministic_and_round_trips() -> None:
    graph = _graph()
    document = RevisionGraphPersistence.encode(graph)
    restored = RevisionGraphPersistence.decode(document)
    assert RevisionGraphPersistence.encode(restored) == document
    assert restored.current.revision_id == graph.current.revision_id
    assert restored.size == graph.size


def test_duplicate_json_keys_are_rejected() -> None:
    document = RevisionGraphPersistence.encode(_graph())
    duplicate = document.replace(
        '"schema_version":1',
        '"schema_version":1,"schema_version":1',
        1,
    )
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(duplicate)


@pytest.mark.parametrize("document", ["", "{", "[]", '{"schema_version":1}'])
def test_malformed_documents_are_rejected(document: str) -> None:
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(document)


def test_wrong_schema_version_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["schema_version"] = 2
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def test_missing_root_or_current_revision_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["root_revision_id"] = "0" * 64
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))

    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["current_revision_id"] = "f" * 64
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def test_orphan_parent_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["revisions"][1]["parent_id"] = "0" * 64
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def test_duplicate_revision_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["revisions"].append(payload["revisions"][0])
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def test_corrupted_revision_identity_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["revisions"][0]["revision_id"] = "0" * 64
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def test_invalid_current_revision_type_is_rejected() -> None:
    payload = json.loads(RevisionGraphPersistence.encode(_graph()))
    payload["current_revision_id"] = None
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(json.dumps(payload, separators=(",", ":"), sort_keys=True))


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_numbers_are_rejected(number: str) -> None:
    document = RevisionGraphPersistence.encode(_graph())
    injected = document.replace(
        '"schema_version":1',
        f'"schema_version":{number}',
        1,
    )
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(injected)


def test_document_size_limit_is_explicit() -> None:
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.encode(_graph(), max_document_bytes=1)
    assert DEFAULT_MAX_DOCUMENT_BYTES > 0


def test_revision_count_limit_is_explicit() -> None:
    graph = _graph()
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.encode(graph, max_revisions=1)
    assert DEFAULT_MAX_REVISIONS >= graph.size


def test_persistence_does_not_mutate_the_graph() -> None:
    graph = _graph()
    before = graph.current.revision_id, graph.size
    document = RevisionGraphPersistence.encode(graph)
    restored = RevisionGraphPersistence.decode(document)
    assert (graph.current.revision_id, graph.size) == before
    assert restored.current.revision_id == before[0]


def test_non_canonical_documents_are_rejected() -> None:
    canonical = RevisionGraphPersistence.encode(_graph())
    payload = json.loads(canonical)
    noncanonical = json.dumps(payload, indent=2, ensure_ascii=False)
    with pytest.raises(PersistenceValidationError):
        RevisionGraphPersistence.decode(noncanonical)
