"""Contract tests for deterministic temporal layer composition."""
from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.blend import BlendMode
from ai_gif_studio.temporal_engine.keyframed_transforms import (
    AffineTransformKeyframe,
    AffineTransformTrack,
)
from ai_gif_studio.temporal_engine.motion_layer import MotionLayer
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.temporal_compositor import composite_motion_layers

pytestmark = pytest.mark.unit


def _buffer(rgb: tuple[float, float, float]) -> RenderBuffer:
    data = np.zeros((20, 30, 4), dtype=np.float32)
    data[..., :3] = rgb
    data[..., 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def _track(offset_x: float) -> AffineTransformTrack:
    return AffineTransformTrack(
        width=30,
        height=20,
        keyframes=(
            AffineTransformKeyframe(
                0.0,
                np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
            ),
            AffineTransformKeyframe(
                1.0,
                np.asarray([[1.0, 0.0, offset_x], [0.0, 1.0, 0.0]]),
            ),
        ),
    )


def test_composite_motion_layers_samples_in_declaration_order() -> None:
    base = _buffer((0.0, 0.0, 0.0))
    first = MotionLayer(_buffer((1.0, 0.0, 0.0)), _track(0.0))
    second = MotionLayer(
        _buffer((0.0, 0.0, 1.0)),
        _track(0.0),
        mode=BlendMode.SCREEN,
    )

    result = composite_motion_layers(base, [first, second], 0.5)

    expected_rgb = np.broadcast_to(np.array((1.0, 0.0, 1.0), dtype=np.float32), result.data[..., :3].shape)
    np.testing.assert_allclose(result.data[..., :3], expected_rgb)
    np.testing.assert_allclose(result.data[..., 3], 1.0)


def test_composite_motion_layers_reuses_motion_layers_without_mutation() -> None:
    base = _buffer((0.1, 0.1, 0.1))
    layer = MotionLayer(_buffer((0.7, 0.2, 0.3)), _track(4.0))
    before = layer.source.data.copy()

    first = composite_motion_layers(base, [layer], 0.25)
    second = composite_motion_layers(base, [layer], 0.25)

    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(layer.source.data, before)
    np.testing.assert_array_equal(base.data, _buffer((0.1, 0.1, 0.1)).data)


def test_composite_motion_layers_empty_sequence_returns_independent_base_copy() -> None:
    base = _buffer((0.2, 0.3, 0.4))

    result = composite_motion_layers(base, (), 0.5)

    np.testing.assert_array_equal(result.data, base.data)
    assert result is not base


def test_composite_motion_layers_rejects_invalid_contracts() -> None:
    base = _buffer((0.0, 0.0, 0.0))
    with pytest.raises(TypeError, match="base"):
        composite_motion_layers(object(), (), 0.5)
    with pytest.raises(ValueError, match="finite"):
        composite_motion_layers(base, (), float("nan"))
    with pytest.raises(TypeError, match="MotionLayer"):
        composite_motion_layers(base, [object()], 0.5)
