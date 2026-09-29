from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Final

import numpy as np

DEFAULT_RENDER_INTERMEDIATE_BUFFERS: Final[int] = 8


class ResourceLimitError(RuntimeError):
    """Raised when a request cannot be admitted within the configured resource budget."""


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    memory_bytes: int
    model: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.memory_bytes, bool) or not isinstance(self.memory_bytes, (int, np.integer)):
            raise TypeError("memory_bytes must be an integer")
        if self.memory_bytes <= 0:
            raise ValueError("memory_bytes must be positive")


@dataclass(frozen=True, slots=True)
class ResourceReservation:
    reservation_id: int
    memory_bytes: int
    model: str | None = None


class ResourceManager:
    """Process-local admission controller for bounded render memory.

    Reservation happens before work starts and release is idempotent. The manager
    intentionally does not allocate memory itself; it prevents known over-budget
    work from reaching the execution layer. A shared instance should be injected
    by the application when concurrent jobs must share one process budget.
    """

    def __init__(self, memory_limit_bytes: int) -> None:
        if isinstance(memory_limit_bytes, bool) or not isinstance(memory_limit_bytes, (int, np.integer)):
            raise TypeError("memory_limit_bytes must be an integer")
        if memory_limit_bytes <= 0:
            raise ValueError("memory_limit_bytes must be positive")
        self._limit = memory_limit_bytes
        self._reserved = 0
        self._next_id = 1
        self._active: dict[int, ResourceReservation] = {}
        self._lock = Lock()

    @staticmethod
    def estimate_render_memory_bytes(
        width: int,
        height: int,
        layers: int,
        *,
        channels: int = 4,
        dtype: np.dtype | type[np.floating] = np.float32,
        intermediate_dtype: np.dtype | type[np.floating] = np.float64,
        intermediate_buffers: int = DEFAULT_RENDER_INTERMEDIATE_BUFFERS,
    ) -> int:
        """Return a conservative pre-allocation budget for RGBA compositing.

        The estimate includes the base plus all source layers and a fixed
        conservative allowance for transient compositor intermediates. It is
        an admission estimate, not a measurement of allocator RSS.
        """
        values = (width, height, layers, channels, intermediate_buffers)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            for value in values
        ):
            raise TypeError(
                "render dimensions, layers, channels, and intermediate_buffers "
                "must be integers"
            )
        if width < 1 or height < 1 or layers < 0 or channels < 1 or intermediate_buffers < 0:
            raise ValueError(
                "render dimensions must be positive and buffer counts non-negative"
            )
        buffer_bytes = int(width) * int(height) * int(channels) * np.dtype(dtype).itemsize
        intermediate_bytes = (
            int(width)
            * int(height)
            * int(channels)
            * np.dtype(intermediate_dtype).itemsize
        )
        return buffer_bytes * (1 + int(layers)) + intermediate_bytes * int(intermediate_buffers)

    @property
    def memory_limit_bytes(self) -> int:
        return self._limit

    @property
    def reserved_bytes(self) -> int:
        with self._lock:
            return self._reserved

    @property
    def available_bytes(self) -> int:
        with self._lock:
            return self._limit - self._reserved

    def reserve(self, request: ResourceRequest) -> ResourceReservation:
        with self._lock:
            if request.memory_bytes > self._limit:
                raise ResourceLimitError(
                    f"resource request requires {request.memory_bytes} bytes; "
                    f"configured limit is {self._limit} bytes"
                )
            if self._reserved + request.memory_bytes > self._limit:
                raise ResourceLimitError(
                    f"resource request would exceed available budget: "
                    f"requested {request.memory_bytes} bytes, available {self._limit - self._reserved} bytes"
                )
            reservation = ResourceReservation(self._next_id, request.memory_bytes, request.model)
            self._next_id += 1
            self._active[reservation.reservation_id] = reservation
            self._reserved += reservation.memory_bytes
            return reservation

    def release(self, reservation: ResourceReservation) -> None:
        with self._lock:
            active = self._active.pop(reservation.reservation_id, None)
            if active is not None:
                self._reserved -= active.memory_bytes
