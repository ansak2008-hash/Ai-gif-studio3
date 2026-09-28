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

pytestmark = pytest.mark.unit


def _source() -> RenderBuffer:
    data = np.zeros((20, 30, 4), dtype=np.float32)
    data[..., 0] = 1.0
    data[..., 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def _track() -> AffineTransformTrack:
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
                np.asarray([[1.0, 0.0, 5.0], [0.0, 1.0, 0.0]]),
            ),
        ),
    )


def test_motion_layer_samples_to_existing_blend_layer() -> None:
    layer = MotionLayer(_source(), _track(), BlendMode.SCREEN)
    result = layer.sample(0.5)

    assert result.mode is BlendMode.SCREEN
    assert result.source is not layer.source
    assert result.source.shape == layer.source.shape
    assert float(result.source.data[..., 3].max()) == 1.0


def test_motion_layer_preserves_source_and_is_reusable() -> None:
    layer = MotionLayer(_source(), _track())
    before = layer.source.data.copy()

    first = layer.sample(0.25).source.data
    second = layer.sample(0.25).source.data

    np.testing.assert_array_equal(layer.source.data, before)
    np.testing.assert_array_equal(first, second)
    assert first is not second


def test_motion_layer_rejects_dimension_and_mode_contract_violations() -> None:
    with pytest.raises(ValueError, match="source dimensions"):
        MotionLayer(
            _source(),
            AffineTransformTrack(
                width=31,
                height=20,
                keyframes=_track().keyframes,
            ),
        )
    with pytest.raises(TypeError, match="BlendMode"):
        MotionLayer(_source(), _track(), mode="screen")
