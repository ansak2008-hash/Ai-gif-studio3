from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


class ResourceLimitError(RuntimeError):
    """Raised when a request cannot be admitted within the configured resource budget."""


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    memory_bytes: int
    model: str | None = None

    def __post_init__(self) -> None:
        if self.memory_bytes <= 0:
            raise ValueError("memory_bytes must be positive")


@dataclass(frozen=True, slots=True)
class ResourceReservation:
    reservation_id: int
    memory_bytes: int
    model: str | None = None


class ResourceManager:
    """Process-local admission controller for bounded accelerator memory.

    Reservation happens before work starts and release is idempotent. The manager
    intentionally does not allocate device memory itself; it prevents known
    over-budget jobs from reaching the execution layer.
    """

    def __init__(self, memory_limit_bytes: int) -> None:
        if memory_limit_bytes <= 0:
            raise ValueError("memory_limit_bytes must be positive")
        self._limit = memory_limit_bytes
        self._reserved = 0
        self._next_id = 1
        self._active: dict[int, ResourceReservation] = {}
        self._lock = Lock()

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
