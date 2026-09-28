from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.color_effects import ExposureEffect
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer() -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[[1.0, 2.0, 4.0, 0.25]]], dtype=np.float32)
    )


def test_exposure_scales_linear_rgb_and_preserves_alpha() -> None:
    result = ExposureEffect(1.0)((_buffer(),))
    expected = np.asarray([[[2.0, 4.0, 8.0, 0.25]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_zero_exposure_returns_independent_equal_values() -> None:
    source = _buffer()
    result = ExposureEffect(0.0)((source,))
    np.testing.assert_array_equal(result.data, source.data)
    assert result is not source


def test_exposure_rejects_nonfinite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        ExposureEffect(float("nan"))


def test_exposure_rejects_wrong_input_count() -> None:
    effect = ExposureEffect(1.0)
    with pytest.raises(ValueError, match="exactly one"):
        effect(())


def test_exposure_rejects_wrong_input_type() -> None:
    effect = ExposureEffect(1.0)
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_exposure_does_not_mutate_source() -> None:
    source = _buffer()
    before = source.data.copy()
    ExposureEffect(2.0)((source,))
    np.testing.assert_array_equal(source.data, before)


def test_exposure_is_deterministic() -> None:
    source = _buffer()
    first = ExposureEffect(-0.5)((source,))
    second = ExposureEffect(-0.5)((source,))
    np.testing.assert_array_equal(first.data, second.data)
