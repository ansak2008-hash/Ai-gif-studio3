from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings

pytestmark = pytest.mark.unit


def _design() -> DesignSpec:
    return DesignSpec()


def _processing() -> ProcessingSettings:
    return ProcessingSettings()


def test_project_state_is_an_immutable_snapshot() -> None:
    project_id = uuid4()
    design = _design()
    metadata = {"title": "demo", "tags": ["a", "b"]}
    state = ProjectState(project_id, 0, design, _processing(), metadata)

    metadata["tags"].append("mutated")
    design.layers.append({"type": "shape", "color": "#fff"})

    assert state.revision == 0
    assert state.project_id == project_id
    assert state.metadata == {"title": "demo", "tags": ["a", "b"]}
    assert state.design.layers == []

    detached = state.metadata
    detached["tags"].append("detached")
    assert state.metadata == {"title": "demo", "tags": ["a", "b"]}

    with pytest.raises((AttributeError, TypeError)):
        state.revision = 1  # type: ignore[misc]


def test_project_state_canonical_json_is_deterministic() -> None:
    project_id = UUID("12345678-1234-5678-1234-567812345678")
    left = ProjectState(project_id, 3, _design(), _processing(), {"b": 2, "a": 1})
    right = ProjectState(project_id, 3, _design(), _processing(), {"a": 1, "b": 2})
    assert left.canonical_json == right.canonical_json
    assert left.canonical_json.encode("utf-8") == right.canonical_json.encode("utf-8")


def test_project_state_round_trips_from_canonical_json() -> None:
    state = ProjectState(uuid4(), 2, _design(), _processing(), {"source": "upload"})
    restored = ProjectState.from_canonical_json(state.canonical_json)
    assert restored.canonical_json == state.canonical_json
    assert restored.project_id == state.project_id
    assert restored.revision == state.revision


@pytest.mark.parametrize(
    "bad_revision",
    [-1, True, False, 1.5],
)
def test_project_state_rejects_invalid_revision(bad_revision: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ProjectState(uuid4(), bad_revision, _design(), _processing(), {})  # type: ignore[arg-type]


def test_project_state_rejects_non_json_metadata() -> None:
    with pytest.raises(TypeError):
        ProjectState(uuid4(), 0, _design(), _processing(), {"bad": object()})


def test_project_state_rejects_noncanonical_domain_inputs() -> None:
    with pytest.raises(TypeError):
        ProjectState(uuid4(), 0, {}, _processing(), {})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ProjectState(uuid4(), 0, _design(), {}, {})  # type: ignore[arg-type]


def test_project_state_canonical_payload_has_explicit_versions() -> None:
    state = ProjectState(uuid4(), 0, _design(), _processing(), {})
    payload = json.loads(state.canonical_json)
    assert payload["design"]["schema_version"] == 3
    assert payload["processing"]["schema_version"] == 2
