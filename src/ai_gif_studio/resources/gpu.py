from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .manager import ResourceLimitError, ResourceManager, ResourceRequest, ResourceReservation


@dataclass(frozen=True, slots=True)
class GpuMemorySnapshot:
    total_bytes: int
    free_bytes: int
    used_bytes: int

    def __post_init__(self) -> None:
        if min(self.total_bytes, self.free_bytes, self.used_bytes) < 0:
            raise ValueError("GPU memory values cannot be negative")
        if self.free_bytes + self.used_bytes > self.total_bytes:
            raise ValueError("GPU memory values are inconsistent")


class GpuManager:
    """Small NVIDIA runtime adapter plus safe admission checks.

    A missing nvidia-smi is treated as unavailable rather than as unlimited VRAM.
    """

    def __init__(self, resource_manager: ResourceManager, executable: str = "nvidia-smi") -> None:
        self._resources = resource_manager
        self._executable = executable

    def snapshot(self) -> GpuMemorySnapshot | None:
        if shutil.which(self._executable) is None:
            return None
        completed = subprocess.run(
            [self._executable, "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        line = completed.stdout.strip().splitlines()[0]
        total, used, free = (int(value.strip()) * 1024**2 for value in line.split(","))
        return GpuMemorySnapshot(total, free, used)

    def reserve(self, memory_bytes: int, model: str | None = None) -> ResourceReservation:
        snapshot = self.snapshot()
        if snapshot is not None and memory_bytes > snapshot.free_bytes:
            raise ResourceLimitError(
                f"GPU request requires {memory_bytes} bytes but only {snapshot.free_bytes} bytes are free"
            )
        return self._resources.reserve(ResourceRequest(memory_bytes, model=model))

    def release(self, reservation: ResourceReservation) -> None:
        self._resources.release(reservation)
