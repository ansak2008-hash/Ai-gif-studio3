import pytest

from ai_gif_studio.resources import ResourceLimitError, ResourceManager, ResourceRequest


@pytest.mark.unit
def test_request_above_limit_is_rejected_before_execution() -> None:
    manager = ResourceManager(8 * 1024**3)
    with pytest.raises(ResourceLimitError, match="configured limit"):
        manager.reserve(ResourceRequest(10 * 1024**3, model="example"))
    assert manager.reserved_bytes == 0


@pytest.mark.unit
def test_reservations_are_bounded_and_released() -> None:
    manager = ResourceManager(8 * 1024**3)
    first = manager.reserve(ResourceRequest(5 * 1024**3))
    with pytest.raises(ResourceLimitError, match="available budget"):
        manager.reserve(ResourceRequest(4 * 1024**3))
    assert manager.reserved_bytes == 5 * 1024**3
    manager.release(first)
    manager.release(first)
    assert manager.reserved_bytes == 0


@pytest.mark.unit
def test_render_memory_estimate_covers_4k_50_layers() -> None:
    requested = ResourceManager.estimate_render_memory_bytes(3840, 2160, 50)
    float32_buffer = 3840 * 2160 * 4 * 4
    float64_intermediate = 3840 * 2160 * 4 * 8
    assert requested == float32_buffer * (1 + 50) + float64_intermediate * 8
    assert requested > 8 * 1024**3


@pytest.mark.unit
def test_4k_50_layer_render_is_rejected_before_execution() -> None:
    manager = ResourceManager(4 * 1024**3)
    requested = manager.estimate_render_memory_bytes(3840, 2160, 50)
    with pytest.raises(ResourceLimitError, match="configured limit"):
        manager.reserve(ResourceRequest(requested, model="cpu-render"))
    assert manager.reserved_bytes == 0
