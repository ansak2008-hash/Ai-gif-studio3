from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.domain.transforms import TransformState
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.transform_binding import apply_transform_state


def _canvas() -> RenderBuffer:
    data = np.zeros((320, 320, 4), dtype=np.float32)
    data[120:200, 120:200, :3] = 1.0
    data[120:200, 120:200, 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def test_identity_transform_returns_detached_equivalent_buffer() -> None:
    source = _canvas()
    result = apply_transform_state(source, TransformState())
    assert result is not source
    assert result.shape == source.shape
    np.testing.assert_array_equal(result.data, source.data)
    assert not result.data.flags.writeable


def test_crop_controls_output_geometry() -> None:
    result = apply_transform_state(
        _canvas(),
        TransformState(crop=(40, 60, 120, 100)),
    )
    assert result.width == 120
    assert result.height == 100


def test_scale_and_translation_are_applied_around_crop_center() -> None:
    source = _canvas()
    result = apply_transform_state(
        source,
        TransformState(scale=2.0, x=10.0, y=-5.0),
    )
    assert result.shape == source.shape
    assert result.data.flags.writeable is False
    assert float(result.data[..., 3].sum()) > 0.0


def test_transform_is_deterministic() -> None:
    source = _canvas()
    state = TransformState(scale=1.25, x=7.0, y=-11.0, crop=(10, 20, 240, 220))
    first = apply_transform_state(source, state)
    second = apply_transform_state(source, state)
    np.testing.assert_array_equal(first.data, second.data)


def test_input_is_not_mutated() -> None:
    source = _canvas()
    before = source.data.copy()
    apply_transform_state(source, TransformState(scale=1.5, x=8.0))
    np.testing.assert_array_equal(source.data, before)


def test_render_binding_requires_canonical_320_canvas() -> None:
    source = RenderBuffer.allocate(64, 64)
    with pytest.raises(ValueError, match="320x320"):
        apply_transform_state(source, TransformState())


def test_invalid_transform_state_cannot_reach_render_binding() -> None:
    source = _canvas()
    with pytest.raises(ValueError):
        TransformState(scale=0.0)
    with pytest.raises(ValueError):
        TransformState(crop=(0, 0, 321, 320))
    assert source.width == 320
