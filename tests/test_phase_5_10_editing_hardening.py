from __future__ import annotations

from uuid import uuid4

import pytest

from ai_gif_studio.domain.layer_state import LayerStack, LayerState
from ai_gif_studio.domain.transforms import (
    MAX_COORDINATE,
    CropCommand,
    ScaleCommand,
    TransformState,
    TranslateCommand,
)
from ai_gif_studio.resources import ResourceManager, ResourceRequest


def _layer() -> LayerState:
    return LayerState(uuid4(), uuid4())


def test_translate_rejects_resulting_coordinate_overflow_before_history_mutation() -> None:
    state = TransformState(x=MAX_COORDINATE)
    with pytest.raises(ValueError, match="x"):
        TranslateCommand(0.000001, 0.0).apply(state)
    assert state == TransformState(x=MAX_COORDINATE)


def test_translate_accepts_exact_resulting_coordinate_boundary() -> None:
    state = TransformState(x=MAX_COORDINATE - 1.0, y=-MAX_COORDINATE + 1.0)
    result = TranslateCommand(1.0, -1.0).apply(state)
    assert result == TransformState(x=MAX_COORDINATE, y=-MAX_COORDINATE)


def test_crop_uses_canonical_transform_canvas_bound() -> None:
    assert CropCommand(0, 0, int(MAX_COORDINATE), int(MAX_COORDINATE)).apply(
        TransformState()
    ).crop == (0, 0, int(MAX_COORDINATE), int(MAX_COORDINATE))


def test_layer_stack_rejects_oversized_payload_before_layer_construction() -> None:
    payload = {
        "layers": [{} for _ in range(257)],
        "max_layers": 256,
    }
    import json

    with pytest.raises(ValueError, match="maximum layer count"):
        LayerStack.from_canonical_json(
            json.dumps(payload, separators=(",", ":"), sort_keys=True)
        )


@pytest.mark.parametrize(
    "value",
    [True, False, 1.0, "1024"],
)
def test_resource_request_rejects_non_integer_memory(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ResourceRequest(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, False, 1024.0, "1024"])
def test_resource_manager_rejects_non_integer_limit(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ResourceManager(value)  # type: ignore[arg-type]


def test_resource_manager_reservation_release_remains_exact() -> None:
    manager = ResourceManager(1024)
    reservation = manager.reserve(ResourceRequest(256, model="test"))
    assert manager.reserved_bytes == 256
    manager.release(reservation)
    manager.release(reservation)
    assert manager.reserved_bytes == 0


def test_existing_scale_boundaries_remain_unchanged() -> None:
    assert ScaleCommand(0.01).apply(TransformState()).scale == 0.01
    assert ScaleCommand(64.0).apply(TransformState()).scale == 64.0
