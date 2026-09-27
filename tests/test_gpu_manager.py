import pytest

from ai_gif_studio.resources import (
    GpuManager,
    GpuMemorySnapshot,
    ResourceLimitError,
    ResourceManager,
)


@pytest.mark.unit
def test_gpu_snapshot_validates_memory() -> None:
    snapshot = GpuMemorySnapshot(8 * 1024**3, 6 * 1024**3, 2 * 1024**3)
    assert snapshot.free_bytes == 6 * 1024**3


@pytest.mark.unit
def test_gpu_manager_rejects_when_observed_free_vram_is_too_low(monkeypatch) -> None:
    manager = ResourceManager(8 * 1024**3)
    gpu = GpuManager(manager)
    monkeypatch.setattr(gpu, "snapshot", lambda: GpuMemorySnapshot(8 * 1024**3, 2 * 1024**3, 6 * 1024**3))
    with pytest.raises(ResourceLimitError, match="free"):
        gpu.reserve(3 * 1024**3, model="large-model")
    assert manager.reserved_bytes == 0
