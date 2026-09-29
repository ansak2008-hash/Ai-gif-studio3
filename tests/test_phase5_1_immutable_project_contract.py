from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

import pytest

from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings

pytestmark = pytest.mark.unit


def _state(metadata: dict | None = None) -> ProjectState:
    return ProjectState(
        UUID("12345678-1234-5678-1234-567812345678"),
        7,
        DesignSpec(),
        ProcessingSettings(),
        {} if metadata is None else metadata,
    )


def test_nested_source_mutation_cannot_reach_snapshot() -> None:
    metadata = {"settings": {"width": 1920, "height": 1080}, "tags": ["a", "b"]}
    state = _state(metadata)
    metadata["settings"]["width"] = 1
    metadata["tags"].append("attacker")

    assert state.metadata == {
        "settings": {"width": 1920, "height": 1080},
        "tags": ["a", "b"],
    }


def test_nested_accessor_mutation_cannot_reach_snapshot() -> None:
    state = _state({"settings": {"width": 1920}, "tags": ["a"]})
    view = state.metadata
    view["settings"]["width"] = 1
    view["tags"].append("attacker")

    assert state.metadata == {"settings": {"width": 1920}, "tags": ["a"]}


def test_design_accessor_is_detached() -> None:
    state = _state()
    design = state.design
    design.layers.append({"type": "attacker"})
    assert state.design.layers == []


def test_processing_accessor_is_detached() -> None:
    state = _state()
    processing = state.processing
    assert processing is not state.processing


def test_canonical_bytes_are_bit_identical() -> None:
    state = _state({"z": 3, "a": {"b": 2, "a": 1}})
    first = state.canonical_json.encode("utf-8")
    second = _state({"a": {"a": 1, "b": 2}, "z": 3}).canonical_json.encode("utf-8")

    assert first == second
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()


def test_round_trip_is_canonical_and_detached() -> None:
    state = _state({"unicode": "é", "control": "\u0000"})
    restored = ProjectState.from_canonical_json(state.canonical_json)

    assert restored.canonical_json.encode("utf-8") == state.canonical_json.encode("utf-8")

    view = restored.metadata
    view["x"] = 1
    assert "x" not in restored.metadata


@pytest.mark.parametrize(
    "payload",
    [
        {"project_id": "not-a-uuid", "revision": 0},
        {"project_id": str(uuid4()), "revision": -1},
        {"project_id": str(uuid4()), "revision": True},
        {"project_id": str(uuid4()), "revision": 0, "metadata": {"bad": float("nan")}},
    ],
)
def test_malformed_canonical_payload_is_rejected(payload: dict) -> None:
    base = json.loads(_state().canonical_json)
    base.update(payload)
    with pytest.raises((TypeError, ValueError)):
        ProjectState.from_canonical_json(
            json.dumps(base, sort_keys=True, separators=(",", ":"))
        )


def test_noncanonical_json_is_rejected() -> None:
    state = _state({"a": 1, "b": 2})
    payload = json.loads(state.canonical_json)
    noncanonical_payload = {
        "metadata": payload["metadata"],
        "project_id": payload["project_id"],
        "revision": payload["revision"],
        "design": payload["design"],
        "processing": payload["processing"],
    }
    noncanonical = json.dumps(noncanonical_payload, ensure_ascii=False, separators=(",", ":"))
    assert noncanonical != state.canonical_json
    with pytest.raises(ValueError):
        ProjectState.from_canonical_json(noncanonical)
