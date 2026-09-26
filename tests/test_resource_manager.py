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
