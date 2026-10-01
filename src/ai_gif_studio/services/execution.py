from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from weakref import WeakKeyDictionary
from typing import Any

from ai_gif_studio.domain.commands import ProjectCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.services.project_editor import ProjectEditor


class AdmissionRejectedError(RuntimeError):
    """Raised when execution cannot be admitted under the configured limit."""


@dataclass(frozen=True, slots=True)
class _OwnershipToken:
    coordinator: object
    sequence: int


BeforeCommit = Callable[[int], Awaitable[None] | None]


class ProjectExecutionCoordinator:
    """Serialize ProjectEditor mutation and bound concurrent execution.

    Coordination state belongs to this coordinator instance; it is never stored
    on ProjectEditor and therefore cannot become process-global project state.
    """

    def __init__(self, *, max_concurrent: int | None = None) -> None:
        if max_concurrent is not None:
            if isinstance(max_concurrent, bool) or not isinstance(max_concurrent, int):
                raise TypeError("max_concurrent must be an integer or None")
            if max_concurrent < 0:
                raise ValueError("max_concurrent must be non-negative or None")
        self._limit = max_concurrent
        self._active = 0
        self._next_sequence = 1
        self._owners: set[_OwnershipToken] = set()
        self._condition = asyncio.Condition()
        self._locks: WeakKeyDictionary[ProjectEditor, asyncio.Lock] = WeakKeyDictionary()

    def _editor_lock(self, editor: ProjectEditor) -> asyncio.Lock:
        if not isinstance(editor, ProjectEditor):
            raise TypeError("editor must be a ProjectEditor")
        lock = self._locks.get(editor)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[editor] = lock
        return lock

    def _new_token(self) -> _OwnershipToken:
        token = _OwnershipToken(self, self._next_sequence)
        self._next_sequence += 1
        self._owners.add(token)
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
        """Acquire an ownership token for explicit boundary testing/integration."""
        if self._limit == 0:
            raise AdmissionRejectedError("execution admission is disabled")
        if self._limit is not None and self._active >= self._limit:
            raise AdmissionRejectedError("execution admission limit reached")
        return self._new_token()

    def release(self, token: _OwnershipToken) -> None:
        if not isinstance(token, _OwnershipToken) or token.coordinator is not self:
            raise ValueError("ownership token does not belong to this coordinator")
        if token not in self._owners:
            return
        self._owners.remove(token)
        self._active -= 1
        if self._active < 0:
            self._active = 0
            raise RuntimeError("execution ownership accounting underflow")
        if self._condition.locked():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._notify_waiters())

    async def _notify_waiters(self) -> None:
        async with self._condition:
            self._condition.notify_all()

    async def execute(
        self,
        editor: ProjectEditor,
        command: ProjectCommand,
        command_metadata: Mapping[str, Any],
        *,
        before_commit: BeforeCommit | None = None,
    ) -> ProjectState:
        if not isinstance(editor, ProjectEditor):
            raise TypeError("editor must be a ProjectEditor")
        lock = self._editor_lock(editor)

        async with lock:
            token = await self._acquire_async()
            primary_error: BaseException | None = None
            try:
                if before_commit is not None:
                    result = before_commit(token.sequence)
                    if inspect.isawaitable(result):
                        await result
                return editor.execute(command, command_metadata)
            except BaseException as exc:
                primary_error = exc
                raise
            finally:
                try:
                    self.release(token)
                except BaseException:
                    if primary_error is not None:
                        raise primary_error
                    raise
