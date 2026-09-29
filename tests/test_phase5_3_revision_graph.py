from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from ai_gif_studio.domain.commands import (
    CommandHistory,
    ReplaceDesignSpecCommand,
)
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.revisions import (
    Revision,
    RevisionGraph,
    RevisionGraphError,
    RevisionLimitError,
    RevisionNotFoundError,
    RevisionValidationError,
)
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings


def _state(revision: int = 0) -> ProjectState:
    return ProjectState(uuid4(), revision, DesignSpec(), ProcessingSettings(), {})


def _root() -> Revision:
    return Revision.create(_state(), None, {"command": "root"})


def _child(parent: Revision, revision: int = 1, marker: str = "edit") -> Revision:
    state = ProjectState(
        parent.state.project_id,
        revision,
        DesignSpec(),
        parent.state.processing,
        {"marker": marker},
    )
    return Revision.create(state, parent.revision_id, {"command": marker})


def test_revision_identity_is_deterministic() -> None:
    state = _state()
    first = Revision.create(state, None, {"command": "root", "value": 1})
    second = Revision.create(state, None, {"value": 1, "command": "root"})
    assert first.revision_id == second.revision_id
    assert first.canonical_json == second.canonical_json


def test_revision_is_immutable_and_detached_from_metadata_input() -> None:
    metadata = {"command": "root", "nested": {"value": 1}}
    revision = Revision.create(_state(), None, metadata)
    metadata["nested"]["value"] = 999
    with pytest.raises((AttributeError, TypeError)):
        revision.parent_id = "x"  # type: ignore[misc]
    assert '"value":1' in revision.command_metadata


def test_root_and_parent_contract() -> None:
    root = _root()
    graph = RevisionGraph(root)
    child = _child(root)
    graph.add(child)
    assert graph.size == 2
    assert graph.current == root
    assert graph.is_ancestor(root.revision_id, child.revision_id)


def test_branching_and_checkout() -> None:
    root = _root()
    graph = RevisionGraph(root)
    left = _child(root, marker="left")
    right = _child(root, marker="right")
    graph.add(left)
    graph.add(right)
    assert graph.is_ancestor(root.revision_id, left.revision_id)
    assert graph.is_ancestor(root.revision_id, right.revision_id)
    assert not graph.is_ancestor(left.revision_id, right.revision_id)
    assert graph.checkout(right.revision_id) == right


def test_ancestry_is_parent_first_and_root_terminated() -> None:
    root = _root()
    graph = RevisionGraph(root)
    one = _child(root)
    two = Revision.create(
        ProjectState(root.state.project_id, 2, DesignSpec(), root.state.processing, {"marker": "two"}),
        one.revision_id,
        {"command": "two"},
    )
    graph.add(one)
    graph.add(two)
    assert graph.ancestry(two.revision_id) == (
        two.revision_id,
        one.revision_id,
        root.revision_id,
    )


def test_invalid_parent_and_orphan_are_rejected() -> None:
    root = _root()
    graph = RevisionGraph(root)
    orphan_parent = "0" * 64
    orphan = Revision.create(_state(1), orphan_parent, {"command": "orphan"})
    with pytest.raises(RevisionValidationError):
        graph.add(orphan)
    with pytest.raises(RevisionNotFoundError):
        graph.get("1" * 64)


def test_duplicate_revision_is_rejected() -> None:
    root = _root()
    graph = RevisionGraph(root)
    with pytest.raises(RevisionValidationError):
        graph.add(root)


def test_max_nodes_is_bounded() -> None:
    root = _root()
    graph = RevisionGraph(root, max_nodes=2)
    graph.add(_child(root))
    with pytest.raises(RevisionLimitError):
        graph.add(_child(root, marker="third"))


def test_corrupted_graph_is_detected() -> None:
    root = _root()
    graph = RevisionGraph(root)
    child = _child(root)
    graph.add(child)
    graph._nodes[child.revision_id] = Revision.create(  # type: ignore[attr-defined]
        _state(1), root.revision_id, {"command": "tampered"}
    )
    with pytest.raises(RevisionValidationError):
        graph.validate()


def test_serialization_round_trip_and_corruption_detection() -> None:
    root = _root()
    restored = Revision.from_canonical_json(root.canonical_json)
    assert restored == root
    corrupted = root.canonical_json.replace(root.revision_id, "0" * 64, 1)
    with pytest.raises(RevisionGraphError):
        Revision.from_canonical_json(corrupted)


def test_undo_redo_states_can_be_materialized_as_revision_branches() -> None:
    initial = _state()
    history = CommandHistory(initial)
    updated = history.execute(ReplaceDesignSpecCommand(DesignSpec()))
    root = Revision.create(initial, None, {"command": "initial"})
    graph = RevisionGraph(root)
    edited = Revision.create(updated, root.revision_id, {"command": "replace_design"})
    graph.add(edited)
    assert graph.checkout(root.revision_id).state == initial
    assert graph.checkout(edited.revision_id).state == updated


def test_deep_graph_is_iterative_and_bounded() -> None:
    root = _root()
    graph = RevisionGraph(root, max_nodes=200)
    previous = root
    for index in range(1, 200):
        current = Revision.create(
            ProjectState(
                root.state.project_id,
                index,
                DesignSpec(),
                root.state.processing,
                {"index": index},
            ),
            previous.revision_id,
            {"command": "deep", "index": index},
        )
        graph.add(current)
        previous = current
    assert len(graph.ancestry(previous.revision_id)) == 200
    with pytest.raises(RevisionLimitError):
        graph.add(_child(previous, 201, "overflow"))


def test_concurrent_reads_are_safe() -> None:
    root = _root()
    graph = RevisionGraph(root)
    child = _child(root)
    graph.add(child)

    def read() -> bool:
        return graph.is_ancestor(root.revision_id, child.revision_id)

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(lambda _: read(), range(100)))
