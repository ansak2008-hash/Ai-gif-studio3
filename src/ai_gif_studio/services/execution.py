from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal
from weakref import WeakKeyDictionary

from ai_gif_studio.domain.commands import ProjectCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.services.project_editor import ProjectEditor

ExecutionState = Literal["pending", "running", "committed", "cancelled", "failed"]


class AdmissionRejectedError(RuntimeError):
    """Raised when execution cannot be admitted under the configured limit."""


class _OwnershipToken:
    __slots__ = ("coordinator", "sequence", "released")

    def __init__(self, coordinator: ProjectExecutionCoordinator, sequence: int) -> None:
        self.coordinator = coordinator
        self.sequence = sequence
        self.released = False


BeforeSubmit = Callable[[], Awaitable[None] | None]


class SubmissionHandle:
    """Awaitable handle for one synchronously submitted editor command."""

    __slots__ = (
        "_cancel_requested",
        "_future",
        "_sequence",
        "_state",
    )

    def __init__(
        self,
        *,
        future: asyncio.Future[ProjectState],
        sequence: int,
    ) -> None:
        self._future = future
        self._sequence = sequence
        self._state: ExecutionState = "pending"
        self._cancel_requested = False

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def state(self) -> ExecutionState:
        return self._state

    def cancel(self) -> bool:
        """Cancel the submission if it has not started executing."""
        if self._state != "pending":
            return False
        self._cancel_requested = True
        self._state = "cancelled"
        self._future.cancel()
        return True

    async def wait(self) -> ProjectState:
        """Wait for the submission without cancelling it when the waiter is cancelled."""
        return await asyncio.shield(self._future)

    def __await__(self):
        return self.wait().__await__()


class _Submission:
    __slots__ = ("command", "handle", "metadata")

    def __init__(
        self,
        command: ProjectCommand,
        handle: SubmissionHandle,
        metadata: Mapping[str, Any],
    ) -> None:
        self.command = command
        self.handle = handle
        self.metadata = metadata


class _EditorQueue:
    __slots__ = ("items", "running")

    def __init__(self) -> None:
        self.items: deque[_Submission] = deque()
        self.running = False


class ProjectExecutionCoordinator:
    """Coordinate deterministic ProjectEditor execution at a service boundary."""

    def __init__(self, *, max_concurrent: int | None = None) -> None:
        if max_concurrent is not None:
            if isinstance(max_concurrent, bool) or not isinstance(max_concurrent, int):
                raise TypeError("max_concurrent must be an integer or None")
            if max_concurrent < 0:
                raise ValueError("max_concurrent must be non-negative or None")
        self._limit = max_concurrent
        self._active = 0
        self._next_submission_sequence = 1
        self._next_admission_sequence = 1
        self._owners: dict[int, _OwnershipToken] = {}
        self._condition = asyncio.Condition()
        self._editor_queues: WeakKeyDictionary[ProjectEditor, _EditorQueue] = WeakKeyDictionary()
        self._loop: asyncio.AbstractEventLoop | None = None

    def _bind_loop(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise RuntimeError("coordinator is bound to a different event loop")
        return loop

    def _validate_submission(
        self,
        editor: ProjectEditor,
        command: ProjectCommand,
        metadata: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        if not isinstance(editor, ProjectEditor):
            raise TypeError("editor must be a ProjectEditor")
        if not isinstance(command, ProjectCommand):
            raise TypeError("command must implement ProjectCommand")
        if metadata is None:
            return {}
        if not isinstance(metadata, Mapping):
            raise TypeError("command_metadata must be a mapping")
        return dict(metadata)

    def submit(
        self,
        editor: ProjectEditor,
        command: ProjectCommand,
        metadata: Mapping[str, Any] | None = None,
    ) -> SubmissionHandle:
        """Synchronously submit a command and allocate its sequence before any await."""
        loop = self._bind_loop()
        command_metadata = self._validate_submission(editor, command, metadata)

        sequence = self._next_submission_sequence
        self._next_submission_sequence += 1

        handle = SubmissionHandle(
            future=loop.create_future(),
            sequence=sequence,
        )
        submission = _Submission(command, handle, command_metadata)
        queue = self._editor_queues.get(editor)
        if queue is None:
            queue = _EditorQueue()
            self._editor_queues[editor] = queue
        queue.items.append(submission)

        if not queue.running:
            queue.running = True
            loop.create_task(self._drain(editor, queue))
        return handle

    async def execute(
        self,
        editor: ProjectEditor,
        command: ProjectCommand,
        command_metadata: Mapping[str, Any],
    ) -> ProjectState:
        """Compatibility wrapper; use submit() when call-site submission order matters."""
        handle = self.submit(editor, command, command_metadata)
        return await handle.wait()

    async def _drain(self, editor: ProjectEditor, queue: _EditorQueue) -> None:
        try:
            while queue.items:
                submission = queue.items.popleft()
                handle = submission.handle
                if handle.state == "cancelled":
                    continue

                token: _OwnershipToken | None = None
                primary_error: BaseException | None = None
                result: ProjectState | None = None
                committed = False

                try:
                    token = await self._acquire_async()
                    if handle.state == "cancelled" or handle._cancel_requested:
                        continue
                    handle._state = "running"
                    result = editor.execute(submission.command, submission.metadata)
                    committed = True
                except BaseException as exc:
                    primary_error = exc
                finally:
                    if token is not None:
                        try:
                            self.release(token)
                        except BaseException as cleanup_error:
                            if primary_error is None:
                                primary_error = cleanup_error
                                committed = False
                            else:
                                primary_error.__cause__ = cleanup_error

                if primary_error is not None:
                    if isinstance(primary_error, asyncio.CancelledError):
                        handle._state = "cancelled"
                        if not handle._future.done():
                            handle._future.cancel()
                    else:
                        handle._state = "failed"
                        if not handle._future.done():
                            handle._future.set_exception(primary_error)
                elif committed:
                    handle._state = "committed"
                    if not handle._future.done():
                        handle._future.set_result(result)
                else:
                    handle._state = "cancelled"
                    if not handle._future.done():
                        handle._future.cancel()
        except BaseException:
            while queue.items:
                pending = queue.items.popleft()
                if pending.handle.state == "pending":
                    pending.handle._state = "failed"
                    if not pending.handle._future.done():
                        pending.handle._future.set_exception(
                            RuntimeError("execution worker terminated unexpectedly")
                        )
            raise
        finally:
            queue.running = False
            current = self._editor_queues.get(editor)
            if current is queue and not queue.items:
                self._editor_queues.pop(editor, None)

    def _new_token(self) -> _OwnershipToken:
        token = _OwnershipToken(self, self._next_admission_sequence)
        self._next_admission_sequence += 1
        self._owners[id(token)] = token
        self._active += 1
        return token

    async def _acquire_async(self) -> _OwnershipToken:
        async with self._condition:
            if self._limit == 0:
                raise AdmissionRejectedError("execution admission is disabled")
            if self._limit is None:
                return self._new_token()
            while self._active >= self._limit:
                await self._condition.wait()
            return self._new_token()

    def acquire(self) -> _OwnershipToken:
        """Acquire an ownership token for explicit boundary testing or integration."""
        self._bind_loop()
        if self._limit == 0:
            raise AdmissionRejectedError("execution admission is disabled")
        if self._limit is not None and self._active >= self._limit:
            raise AdmissionRejectedError("execution admission limit reached")
        return self._new_token()

    def release(self, token: _OwnershipToken) -> None:
        if not isinstance(token, _OwnershipToken) or token.coordinator is not self:
            raise ValueError("ownership token does not belong to this coordinator")
        active = self._owners.get(id(token))
        if active is None:
            if token.released:
                return
            raise ValueError("ownership token is not active")
        if active is not token:
            raise ValueError("ownership token identity mismatch")
        self._owners.pop(id(token))
        token.released = True
        self._active -= 1
        if self._active < 0:
            self._active = 0
            raise RuntimeError("execution ownership accounting underflow")
        loop = self._loop
        if loop is not None and not loop.is_closed():
            loop.create_task(self._notify_waiters())

    async def _notify_waiters(self) -> None:
        async with self._condition:
            self._condition.notify_all()
