from __future__ import annotations

import math

import pytest

from ai_gif_studio.domain.commands import CommandHistory
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.domain.transforms import (
    CropCommand,
    ScaleCommand,
    TransformState,
    TranslateCommand,
)


def _state() -> ProjectState:
    from uuid import uuid4

    return ProjectState(
        uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {},
    )


def test_transform_state_is_immutable_and_detached() -> None:
    state = TransformState()
    with pytest.raises((AttributeError, TypeError)):
        state.x = 1.0
    assert state == TransformState()
    assert state.metadata == {"x": 0.0, "y": 0.0, "scale": 1.0, "crop": (0, 0, 320, 320)}


def test_transform_state_rejects_non_finite_and_out_of_bounds_values() -> None:
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            TransformState(x=value)
    with pytest.raises(ValueError):
        TransformState(scale=0.0)
    with pytest.raises(ValueError):
        TransformState(scale=64.000001)
    with pytest.raises(ValueError):
        TransformState(x=-320.000001)
    with pytest.raises(ValueError):
        TransformState(x=320.000001)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: CropCommand(-1, 0, 10, 10), "crop"),
        (lambda: CropCommand(0, 0, 321, 10), "crop"),
        (lambda: CropCommand(0, 0, 10, 321), "crop"),
        (lambda: CropCommand(10, 10, 5, 10), "crop"),
        (lambda: ScaleCommand(0.0), "scale"),
        (lambda: ScaleCommand(64.000001), "scale"),
        (lambda: TranslateCommand(320.000001, 0.0), "translate"),
    ],
)
def test_commands_reject_invalid_geometry_before_application(factory, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_crop_scale_translate_are_deterministic() -> None:
    first = TranslateCommand(12.5, -7.25).apply(
        ScaleCommand(2.0).apply(CropCommand(10, 20, 200, 180).apply(TransformState()))
    )
    second = TranslateCommand(12.5, -7.25).apply(
        ScaleCommand(2.0).apply(CropCommand(10, 20, 200, 180).apply(TransformState()))
    )
    assert first == second
    assert first.canonical_json == second.canonical_json


def test_commands_are_immutable_and_have_canonical_metadata() -> None:
    command = TranslateCommand(12.5, -7.25)
    with pytest.raises((AttributeError, TypeError)):
        command.dx = 1.0
    assert command.metadata == {"dx": 12.5, "dy": -7.25}
    assert command.canonical_json == '{"dx":12.5,"dy":-7.25,"operation":"translate"}'


def test_command_application_does_not_mutate_input() -> None:
    original = TransformState()
    result = TranslateCommand(10.0, 5.0).apply(original)
    assert original == TransformState()
    assert result == TransformState(x=10.0, y=5.0)


def test_commands_compose_through_project_command_history() -> None:
    initial = _state()
    history = CommandHistory(initial)
    first = history.execute(TranslateCommand(10.0, 5.0))
    second = history.execute(ScaleCommand(2.0))
    assert first.revision == 1
    assert second.revision == 2
    assert second.transform == TransformState(x=10.0, y=5.0, scale=2.0)
    assert history.undo().transform == first.transform
    assert history.redo().transform == second.transform


def test_transform_commands_have_deterministic_project_metadata() -> None:
    assert TranslateCommand(1.25, 2.5).metadata == {"dx": 1.25, "dy": 2.5}
    assert ScaleCommand(2.0).metadata == {"scale": 2.0}
    assert CropCommand(1, 2, 100, 120).metadata == {
        "x": 1,
        "y": 2,
        "width": 100,
        "height": 120,
    }


def test_transform_command_boundary_values_are_accepted() -> None:
    assert TranslateCommand(320.0, -320.0).apply(TransformState()).x == 320.0
    assert ScaleCommand(64.0).apply(TransformState()).scale == 64.0
    assert CropCommand(0, 0, 320, 320).apply(TransformState()).crop == (
        0,
        0,
        320,
        320,
    )


def test_project_transform_round_trips_canonically() -> None:
    initial = _state()
    transformed = TranslateCommand(12.0, -4.0).apply(initial)
    restored = ProjectState.from_canonical_json(transformed.canonical_json)
    assert restored == transformed
    assert restored.transform == transformed.transform


def test_project_transform_is_detached_from_returned_metadata() -> None:
    transformed = TranslateCommand(12.0, -4.0).apply(_state())
    metadata = transformed.metadata
    metadata["nested"] = {"mutable": True}
    assert "nested" not in transformed.metadata


def test_equivalent_commands_have_identical_canonical_identity() -> None:
    assert TranslateCommand(1.5, 2.5).canonical_json == TranslateCommand(1.5, 2.5).canonical_json
    assert ScaleCommand(2).canonical_json == ScaleCommand(2.0).canonical_json
    assert CropCommand(0, 0, 320, 320).canonical_json == CropCommand(0, 0, 320, 320).canonical_json


def test_commands_reject_wrong_state_type() -> None:
    for command in (
        CropCommand(0, 0, 10, 10),
        ScaleCommand(2.0),
        TranslateCommand(1.0, 1.0),
    ):
        with pytest.raises(TypeError):
            command.apply(object())
