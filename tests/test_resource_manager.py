import pytest

from ai_gif_studio.resources import ResourceLimitError, ResourceManager, ResourceRequest
from ai_gif_studio.resources.manager import ResourceReservation


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

@pytest.mark.unit
def test_reservation_cannot_be_released_by_another_manager() -> None:
    first = ResourceManager(1024)
    second = ResourceManager(1024)
    reservation = first.reserve(ResourceRequest(256))
    with pytest.raises(ValueError, match="reservation does not belong"):
        second.release(reservation)
    assert first.reserved_bytes == 256
    assert second.reserved_bytes == 0
    first.release(reservation)


@pytest.mark.unit
def test_forged_reservation_cannot_change_resource_accounting() -> None:
    manager = ResourceManager(1024)
    reservation = manager.reserve(ResourceRequest(256))
    forged = ResourceReservation(reservation.reservation_id, reservation.memory_bytes)
    with pytest.raises(ValueError, match="reservation does not belong"):
        manager.release(forged)
    assert manager.reserved_bytes == 256
    manager.release(reservation)


@pytest.mark.unit
def test_exact_remaining_budget_is_admitted() -> None:
    manager = ResourceManager(1024)
    first = manager.reserve(ResourceRequest(768))
    second = manager.reserve(ResourceRequest(256))
    assert manager.reserved_bytes == 1024
    assert manager.available_bytes == 0
    manager.release(first)
    manager.release(second)


@pytest.mark.unit
def test_one_byte_over_remaining_budget_is_rejected_without_accounting_change() -> None:
    manager = ResourceManager(1024)
    first = manager.reserve(ResourceRequest(1024))
    with pytest.raises(ResourceLimitError, match="available budget"):
        manager.reserve(ResourceRequest(1))
    assert manager.reserved_bytes == 1024
    manager.release(first)


@pytest.mark.unit
def test_forged_reservation_with_copied_owner_token_cannot_release_active_reservation() -> None:
    manager = ResourceManager(1024)
    reservation = manager.reserve(ResourceRequest(256, model="test"))
    forged = ResourceReservation(
        reservation.reservation_id,
        reservation.memory_bytes,
        reservation.model,
        reservation._owner_token,
    )
    with pytest.raises(ValueError, match="reservation does not belong"):
        manager.release(forged)
    assert manager.reserved_bytes == 256
    manager.release(reservation)
    assert manager.reserved_bytes == 0


@pytest.mark.unit
def test_concurrent_admission_never_exceeds_budget() -> None:
    from concurrent.futures import ThreadPoolExecutor

    manager = ResourceManager(5)

    def attempt() -> ResourceReservation | None:
        try:
            return manager.reserve(ResourceRequest(1))
        except ResourceLimitError:
            return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        reservations = list(executor.map(lambda _: attempt(), range(20)))

    accepted = [reservation for reservation in reservations if reservation is not None]
    assert len(accepted) == 5
    assert manager.reserved_bytes == 5
    assert manager.reserved_bytes <= manager.memory_limit_bytes
    for reservation in accepted:
        manager.release(reservation)
    assert manager.reserved_bytes == 0


@pytest.mark.unit
def test_render_memory_estimate_is_deterministic() -> None:
    first = ResourceManager.estimate_render_memory_bytes(320, 320, 6)
    second = ResourceManager.estimate_render_memory_bytes(320, 320, 6)
    assert first == second
