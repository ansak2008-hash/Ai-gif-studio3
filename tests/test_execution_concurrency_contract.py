from __future__ import annotations

import asyncio

import pytest

from ai_gif_studio.domain.commands import ReplaceDesignSpecCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.services.execution import (
    AdmissionRejectedError,
    ProjectExecutionCoordinator,
)
from ai_gif_studio.services.project_editor import ProjectEditor

pytestmark = pytest.mark.unit


def _state() -> ProjectState:
    return ProjectState(
        __import__("uuid").uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {"fixture": "phase-6-2"},
    )


def _command(color: str) -> ReplaceDesignSpecCommand:
    return ReplaceDesignSpecCommand(
        DesignSpec(background={"mode": "solid", "color": color})
    )


@pytest.mark.asyncio
async def test_same_editor_commands_are_serialized_in_submission_order() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    started: list[int] = []
    release_first = asyncio.Event()
    first_started = asyncio.Event()

    async def first_hook(_sequence: int) -> None:
        started.append(_sequence)
        first_started.set()
        await release_first.wait()

    async def second_hook(sequence: int) -> None:
        started.append(sequence)

    first = asyncio.create_task(
        coordinator.execute(editor, _command("#111111"), {"operation": "first"}, before_commit=first_hook)
    )
    await first_started.wait()
    second = asyncio.create_task(
        coordinator.execute(editor, _command("#222222"), {"operation": "second"}, before_commit=second_hook)
    )

    await asyncio.sleep(0)
    assert editor.revision_count == 1
    release_first.set()

    assert (await first).revision == 1
    assert (await second).revision == 2
    assert started == [1, 2]
    assert editor.current_revision.state.design.background["color"] == "#222222"


@pytest.mark.asyncio
async def test_independent_editors_can_execute_concurrently() -> None:
    first_editor = ProjectEditor.create(_state())
    second_editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    barrier = asyncio.Barrier(2)

    async def hook(_sequence: int) -> None:
        await barrier.wait()

    first, second = await asyncio.gather(
        coordinator.execute(
            first_editor, _command("#111111"), {"operation": "first"}, before_commit=hook
        ),
        coordinator.execute(
            second_editor, _command("#222222"), {"operation": "second"}, before_commit=hook
        ),
    )

    assert first.revision == second.revision == 1
    assert first_editor.revision_count == second_editor.revision_count == 2


@pytest.mark.asyncio
async def test_cancellation_before_command_start_creates_no_revision() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    blocker = asyncio.Event()
    first_started = asyncio.Event()

    async def first_hook(_sequence: int) -> None:
        first_started.set()
        await blocker.wait()

    first = asyncio.create_task(
        coordinator.execute(editor, _command("#111111"), {"operation": "first"}, before_commit=first_hook)
    )
    await first_started.wait()

    second = asyncio.create_task(
        coordinator.execute(editor, _command("#222222"), {"operation": "second"})
    )
    second.cancel()
    with pytest.raises(asyncio.CancelledError):
        await second

    blocker.set()
    assert (await first).revision == 1
    assert editor.revision_count == 2
    assert editor.current_state.design.background["color"] == "#111111"


@pytest.mark.asyncio
async def test_command_failure_leaves_revision_graph_unchanged() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    before = editor.canonical_json

    async def fail(_sequence: int) -> None:
        raise RuntimeError("command boundary failure")

    with pytest.raises(RuntimeError, match="command boundary failure"):
        await coordinator.execute(
            editor,
            _command("#111111"),
            {"operation": "failure"},
            before_commit=fail,
        )

    assert editor.canonical_json == before
    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_global_admission_rejection_does_not_mutate_editor() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator(max_concurrent=0)

    with pytest.raises(AdmissionRejectedError):
        await coordinator.execute(editor, _command("#111111"), {"operation": "rejected"})

    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_ownership_release_is_scoped_and_idempotent() -> None:
    coordinator = ProjectExecutionCoordinator(max_concurrent=1)
    owner = coordinator.acquire()
    forged = object()

    with pytest.raises(ValueError, match="ownership"):
        coordinator.release(forged)

    coordinator.release(owner)
    coordinator.release(owner)


@pytest.mark.asyncio
async def test_release_failure_does_not_mask_primary_command_failure() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    coordinator.fail_next_release()

    async def fail(_sequence: int) -> None:
        raise RuntimeError("primary command failure")

    with pytest.raises(RuntimeError, match="primary command failure"):
        await coordinator.execute(
            editor,
            _command("#111111"),
            {"operation": "failure"},
            before_commit=fail,
        )
    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_admission_sequence_has_no_duplicates_under_concurrency() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    sequences: list[int] = []

    async def hook(sequence: int) -> None:
        sequences.append(sequence)

    await asyncio.gather(
        *(
            coordinator.execute(
                editor,
                _command(f"#{index:06x}"),
                {"operation": f"op-{index}"},
                before_commit=hook,
            )
            for index in range(10)
        )
    )

    assert sequences == list(range(1, 11))
    assert editor.revision_count == 11
