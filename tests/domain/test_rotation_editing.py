from __future__ import annotations

import math
from uuid import uuid4

import numpy as np
import pytest

from ai_gif_studio.domain.commands import CommandHistory
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.domain.transforms import RotateCommand, TransformState
from ai_gif_studio.temporal_engine import apply_transform_state
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer


def _state() -> ProjectState:
    return ProjectState(uuid4(), 0, DesignSpec(), ProcessingSettings(), {})


def _canvas() -> RenderBuffer:
    data = np.zeros((320, 320, 4), dtype=np.float32)
    data[120:200, 140:180, :3] = 1.0
    data[120:200, 140:180, 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def test_rotation_state_is_immutable_and_bounded() -> None:
    state = TransformState(rotation=45.0)
    assert state.rotation == 45.0
    with pytest.raises((AttributeError, TypeError)):
        state.rotation = 90.0
    for value in (math.nan, math.inf, -math.inf, 360.000001, -360.000001):
        with pytest.raises(ValueError):
            TransformState(rotation=value)


def test_rotate_command_is_immutable_and_canonical() -> None:
    command = RotateCommand(22.5)
    with pytest.raises((AttributeError, TypeError)):
        command.degrees = 10.0
    assert command.metadata == {"degrees": 22.5}
    assert command.canonical_json == '{"degrees":22.5,"operation":"rotate"}'


def test_rotate_command_composes_and_preserves_existing_transform() -> None:
    state = TransformState(x=8.0, y=-3.0, scale=1.5, rotation=10.0)
    result = RotateCommand(20.0).apply(state)
    assert result == TransformState(x=8.0, y=-3.0, scale=1.5, rotation=30.0)
    assert state.rotation == 10.0


def test_rotate_command_rejects_invalid_input_before_application() -> None:
    for value in (math.nan, math.inf, -math.inf, 360.000001, -360.000001):
        with pytest.raises(ValueError, match="degrees"):
            RotateCommand(value)


def test_rotate_command_composes_through_project_command_history() -> None:
    history = CommandHistory(_state())
    first = history.execute(RotateCommand(30.0))
    second = history.execute(RotateCommand(-10.0))
    assert first.revision == 1
    assert second.revision == 2
    assert second.transform.rotation == 20.0
    assert history.undo().transform.rotation == 30.0
    assert history.redo().transform.rotation == 20.0


def test_project_rotation_round_trips_canonically() -> None:
    transformed = RotateCommand(37.5).apply(_state())
    restored = ProjectState.from_canonical_json(transformed.canonical_json)
    assert restored == transformed
    assert restored.transform.rotation == 37.5


def test_legacy_project_state_without_rotation_remains_compatible() -> None:
    state = _state()
    restored = ProjectState.from_canonical_json(state.canonical_json)
    assert restored.transform.rotation == 0.0
    assert restored.canonical_json == state.canonical_json


def test_legacy_project_state_with_existing_transform_encoding_remains_compatible() -> None:
    state = TransformState(x=12.0, y=-4.0, scale=1.5)
    project = ProjectState(uuid4(), 3, DesignSpec(), ProcessingSettings(), {}, transform=state)
    restored = ProjectState.from_canonical_json(project.canonical_json)
    assert restored == project
    assert '"rotation"' not in project.canonical_json


def test_rotation_render_binding_preserves_crop_geometry_and_is_deterministic() -> None:
    state = TransformState(crop=(20, 30, 180, 140), rotation=90.0)
    source = _canvas()
    first = apply_transform_state(source, state)
    second = apply_transform_state(source, state)
    assert first.shape == (140, 180, 4)
    np.testing.assert_array_equal(first.data, second.data)
    assert first.data.flags.writeable is False


def test_rotation_does_not_mutate_source() -> None:
    source = _canvas()
    before = source.data.copy()
    apply_transform_state(source, TransformState(rotation=37.5))
    np.testing.assert_array_equal(source.data, before)
