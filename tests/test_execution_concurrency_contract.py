from __future__ import annotations

import asyncio
from uuid import uuid4

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
        uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {"fixture": "phase-6-2"},
    )


def _command(color: str) -> ReplaceDesignSpecCommand:
    return ReplaceDesignSpecCommand(DesignSpec(background={"mode": "solid", "color": color}))


class FailingCommand:
    def apply(self, _state: ProjectState) -> ProjectState:
        raise RuntimeError("command failure")


@pytest.mark.asyncio
async def test_submit_then_await_reverse_order_preserves_submission_order() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(editor, _command("#111111"), {"operation": "first"})
    second = coordinator.submit(editor, _command("#222222"), {"operation": "second"})

    second_result = await second
    first_result = await first

    assert first_result.revision == 1
    assert second_result.revision == 2
    assert editor.current_revision.state.design.background["color"] == "#222222"


@pytest.mark.asyncio
async def test_three_submissions_remain_ordered_when_awaited_in_reverse() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(editor, _command("#111111"), {"operation": "first"})
    second = coordinator.submit(editor, _command("#222222"), {"operation": "second"})
    third = coordinator.submit(editor, _command("#333333"), {"operation": "third"})

    third_result = await third
    second_result = await second
    first_result = await first

    assert first_result.revision == 1
    assert second_result.revision == 2
    assert third_result.revision == 3
    assert editor.current_revision.state.design.background["color"] == "#333333"


@pytest.mark.asyncio
async def test_sequence_is_allocated_before_first_await() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(editor, _command("#111111"))
    second = coordinator.submit(editor, _command("#222222"))

    assert first.sequence == 1
    assert second.sequence == 2
    assert first.sequence < second.sequence
    assert first.state == "pending"
    assert second.state == "pending"


@pytest.mark.asyncio
async def test_high_concurrency_submission_has_unique_contiguous_sequences() -> None:
    coordinator = ProjectExecutionCoordinator()
    editor = ProjectEditor.create(_state())

    async def submit_one(index: int) -> int:
        await asyncio.sleep(0)
        return coordinator.submit(editor, _command(f"#{index:06x}")).sequence

    sequences = await asyncio.gather(*(submit_one(index) for index in range(100)))

    assert sorted(sequences) == list(range(1, 101))


@pytest.mark.asyncio
async def test_pending_cancellation_creates_no_revision() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(editor, _command("#111111"), {"operation": "first"})
    second = coordinator.submit(editor, _command("#222222"), {"operation": "second"})

    assert second.cancel() is True
    assert second.state == "cancelled"

    first_result = await first
    with pytest.raises(asyncio.CancelledError):
        await second

    assert first_result.revision == 1
    assert editor.revision_count == 2
    assert editor.current_state.design.background["color"] == "#111111"


@pytest.mark.asyncio
async def test_cancelling_a_waiter_does_not_cancel_submission() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    handle = coordinator.submit(editor, _command("#111111"))
    waiter = asyncio.create_task(handle.wait())
    waiter.cancel()

    with pytest.raises(asyncio.CancelledError):
        await waiter

    result = await handle
    assert result.revision == 1
    assert handle.state == "committed"
    assert editor.revision_count == 2


@pytest.mark.asyncio
async def test_cancellation_after_commit_preserves_revision() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    handle = coordinator.submit(editor, _command("#111111"))
    result = await handle

    assert result.revision == 1
    assert handle.cancel() is False
    assert handle.state == "committed"
    assert editor.revision_count == 2


@pytest.mark.asyncio
async def test_command_failure_leaves_revision_graph_unchanged() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    before = editor.canonical_json

    handle = coordinator.submit(editor, FailingCommand(), {"operation": "failure"})

    with pytest.raises(RuntimeError, match="command failure"):
        await handle

    assert handle.state == "failed"
    assert editor.canonical_json == before
    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_admission_rejection_does_not_mutate_editor() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator(max_concurrent=0)

    handle = coordinator.submit(editor, _command("#111111"), {"operation": "rejected"})

    with pytest.raises(AdmissionRejectedError):
        await handle

    assert handle.state == "failed"
    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_ownership_release_is_scoped_and_idempotent() -> None:
    coordinator = ProjectExecutionCoordinator(max_concurrent=1)
    owner = coordinator.acquire()
    forged = object()
    copied = type(owner)(owner.coordinator, owner.sequence)

    with pytest.raises(ValueError, match="ownership"):
        coordinator.release(forged)
    with pytest.raises(ValueError, match="ownership"):
        coordinator.release(copied)

    coordinator.release(owner)
    coordinator.release(owner)


@pytest.mark.asyncio
async def test_release_failure_does_not_mask_primary_command_failure() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    original_release = coordinator.release

    def failing_release(token):
        original_release(token)
        raise RuntimeError("release failure")

    coordinator.release = failing_release

    handle = coordinator.submit(editor, FailingCommand(), {"operation": "failure"})

    with pytest.raises(RuntimeError, match="command failure") as caught:
        await handle

    assert isinstance(caught.value.__cause__, RuntimeError)
    assert str(caught.value.__cause__) == "release failure"
    assert editor.revision_count == 1


@pytest.mark.asyncio
async def test_release_failure_after_success_is_observable() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()
    original_release = coordinator.release

    def failing_release(token):
        original_release(token)
        raise RuntimeError("release failure")

    coordinator.release = failing_release

    handle = coordinator.submit(
        editor,
        _command("#111111"),
        {"operation": "successful-command"},
    )

    with pytest.raises(RuntimeError, match="release failure"):
        await handle

    assert handle.state == "failed"
    assert editor.revision_count == 2
    assert editor.current_state.design.background["color"] == "#111111"


@pytest.mark.asyncio
async def test_independent_editors_have_independent_execution_queues() -> None:
    first_editor = ProjectEditor.create(_state())
    second_editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(first_editor, _command("#111111"))
    second = coordinator.submit(second_editor, _command("#222222"))

    first_result, second_result = await asyncio.gather(first, second)

    assert first_result.revision == 1
    assert second_result.revision == 1
    assert first_editor.current_state.design.background["color"] == "#111111"
    assert second_editor.current_state.design.background["color"] == "#222222"


@pytest.mark.asyncio
async def test_canonical_save_load_preserves_current_revision_after_serialized_execution() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = coordinator.submit(editor, _command("#111111"))
    second = coordinator.submit(editor, _command("#222222"))

    await asyncio.gather(first, second)

    restored = ProjectEditor.from_canonical_json(editor.canonical_json)

    assert restored.current_revision_id == editor.current_revision_id
    assert restored.current_state.canonical_json == editor.current_state.canonical_json
    assert restored.revision_count == editor.revision_count


@pytest.mark.asyncio
async def test_execute_compatibility_wrapper_uses_submission_boundary() -> None:
    editor = ProjectEditor.create(_state())
    coordinator = ProjectExecutionCoordinator()

    first = asyncio.create_task(
        coordinator.execute(editor, _command("#111111"), {"operation": "first"})
    )
    second = asyncio.create_task(
        coordinator.execute(editor, _command("#222222"), {"operation": "second"})
    )

    first_result, second_result = await asyncio.gather(first, second)

    assert first_result.revision == 1
    assert second_result.revision == 2
    assert editor.current_revision.state.design.background["color"] == "#222222"
