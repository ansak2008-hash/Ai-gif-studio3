from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine import blend as blend_module
from ai_gif_studio.temporal_engine.blend import BlendMode, BlendModeEffect
from ai_gif_studio.temporal_engine.geometry_transforms import (
    AffineTransformEffect,
    AffineTransformSpec,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer(value: float, alpha: float = 1.0) -> RenderBuffer:
    rgba = np.full((4, 4, 4), value, dtype=np.float32)
    rgba[..., 3] = alpha
    return RenderBuffer.from_linear_rgba(rgba)


def _long_pipeline(source: RenderBuffer, overlay: RenderBuffer) -> RenderBuffer:
    identity = AffineTransformSpec(
        4,
        4,
        np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64),
    )
    result = source
    for index in range(24):
        if index % 2 == 0:
            result = AffineTransformEffect(identity)((result,))
        else:
            result = BlendModeEffect(BlendMode.SCREEN)((result, overlay))
    return result


def test_24_stage_transform_blend_pipeline_is_bit_identical_across_10_runs() -> None:
    source = _buffer(0.25, 0.8)
    overlay = _buffer(0.6, 0.5)

    outputs = [_long_pipeline(source, overlay).data.copy() for _ in range(10)]

    for output in outputs[1:]:
        np.testing.assert_array_equal(output, outputs[0])
        assert output.tobytes() == outputs[0].tobytes()


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_nonfinite_internal_blend_result_is_rejected(monkeypatch, bad_value: float) -> None:
    source = _buffer(0.2, 1.0)
    overlay = _buffer(0.4, 1.0)
    before = source.data.copy()

    def inject_nonfinite(
        _mode: BlendMode,
        destination: np.ndarray,
        _source: np.ndarray,
    ) -> np.ndarray:
        return np.full_like(destination, bad_value)

    monkeypatch.setattr(blend_module, "_blend_rgb", inject_nonfinite)

    with pytest.raises(ValueError, match="finite"):
        BlendModeEffect(BlendMode.NORMAL)((source, overlay))

    np.testing.assert_array_equal(source.data, before)


@pytest.mark.parametrize(
    ("rgb_value", "alpha"),
    [
        (0.0, 0.0),
        (np.finfo(np.float32).tiny, 1.0),
        (1.0e6, 1.0),
        (4.0, 0.0),
        (4.0, 1.0),
    ],
)
def test_extreme_finite_hdr_values_and_alpha_endpoints_remain_canonical(
    rgb_value: float,
    alpha: float,
) -> None:
    source = _buffer(rgb_value, alpha)
    identity = AffineTransformSpec(
        4,
        4,
        np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64),
    )
    result = AffineTransformEffect(identity)((source,))

    assert result.dtype == np.dtype(np.float32)
    assert np.isfinite(result.data).all()
    np.testing.assert_array_equal(result.data, source.data)
