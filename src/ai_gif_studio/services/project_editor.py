from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_gif_studio.domain.commands import ProjectCommand
from ai_gif_studio.domain.persistence import RevisionGraphPersistence
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.revisions import Revision, RevisionGraph


class ProjectEditor:
    """Application boundary for immutable project editing and revision tracking."""

    _ROOT_METADATA = {"operation": "root"}

    def __init__(self, graph: RevisionGraph) -> None:
        if not isinstance(graph, RevisionGraph):
            raise TypeError("graph must be a RevisionGraph")
        graph.validate()
        self._graph = graph

    @classmethod
    def create(cls, initial_state: ProjectState, *, max_revisions: int = 10_000) -> ProjectEditor:
        if not isinstance(initial_state, ProjectState):
            raise TypeError("initial_state must be a ProjectState")
        root = Revision.create(initial_state, None, cls._ROOT_METADATA)
        return cls(RevisionGraph(root, max_nodes=max_revisions))

    @classmethod
    def from_canonical_json(
        cls,
        document: str,
        *,
        max_document_bytes: int = 16 * 1024 * 1024,
        max_revisions: int = 10_000,
    ) -> ProjectEditor:
        graph = RevisionGraphPersistence.decode(
            document,
            max_document_bytes=max_document_bytes,
            max_revisions=max_revisions,
        )
        return cls(graph)

    @property
    def current_revision(self) -> Revision:
        return self._graph.current

    @property
    def current_revision_id(self) -> str:
        return self._graph.current.revision_id

    @property
    def current_state(self) -> ProjectState:
        return self._graph.current.state

    @property
    def revision_count(self) -> int:
        return self._graph.size

    @property
    def canonical_json(self) -> str:
        return RevisionGraphPersistence.encode(self._graph)

    def get_revision(self, revision_id: str) -> Revision:
        return self._graph.get(revision_id)

    def execute(
        self,
        command: ProjectCommand,
        command_metadata: Mapping[str, Any],
    ) -> ProjectState:
        if not isinstance(command, ProjectCommand):
            raise TypeError("command must implement ProjectCommand")
        if not isinstance(command_metadata, Mapping):
            raise TypeError("command_metadata must be a mapping")
        parent = self._graph.current
        next_state = command.apply(parent.state)
        if not isinstance(next_state, ProjectState):
            raise TypeError("command must return a ProjectState")
        if next_state.revision != parent.state.revision + 1:
            raise ValueError("command must increment revision exactly once")
        revision = Revision.create(next_state, parent.revision_id, command_metadata)
        self._graph.add(revision)
        self._graph.checkout(revision.revision_id)
        return next_state

    def checkout(self, revision_id: str) -> ProjectState:
        return self._graph.checkout(revision_id).state
