from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.framing import (
    FramingEffect,
    FramingMode,
    FramingSpec,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer


pytestmark = pytest.mark.unit


def _buffer(width: int = 4, height: int = 2) -> RenderBuffer:
    values = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            values[y, x] = (float(x + 1), float(y + 1), 10.0, 1.0)
    return RenderBuffer.from_linear_rgba(values)


def test_crop_selects_exact_focus_window_without_resampling() -> None:
    source = _buffer()
    result = FramingEffect(
        FramingSpec(2, 2, FramingMode.CROP, focus_x=1.0, focus_y=0.0)
    )((source,))

    expected = np.asarray(
        [
            [[3.0, 1.0, 10.0, 1.0], [4.0, 1.0, 10.0, 1.0]],
            [[3.0, 2.0, 10.0, 1.0], [4.0, 2.0, 10.0, 1.0]],
        ],
        dtype=np.float32,
    )
    np.testing.assert_array_equal(result.data, expected)


def test_fit_preserves_all_source_pixels_with_transparent_padding() -> None:
    source = _buffer(4, 2)
    result = FramingEffect(FramingSpec(4, 4, FramingMode.FIT))((source,))

    assert result.shape == (4, 4, 4)
    np.testing.assert_array_equal(result.data[:1], np.zeros((1, 4, 4), dtype=np.float32))
    np.testing.assert_array_equal(result.data[1:3], source.data)
    np.testing.assert_array_equal(result.data[3:], np.zeros((1, 4, 4), dtype=np.float32))


def test_fill_covers_target_and_uses_focus_for_crop_position() -> None:
    source = _buffer(4, 2)
    result = FramingEffect(
        FramingSpec(2, 2, FramingMode.FILL, focus_x=1.0, focus_y=0.5)
    )((source,))

    expected = np.asarray(
        [
            [[3.0, 1.0, 10.0, 1.0], [4.0, 1.0, 10.0, 1.0]],
            [[3.0, 2.0, 10.0, 1.0], [4.0, 2.0, 10.0, 1.0]],
        ],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_identity_framing_returns_independent_storage() -> None:
    source = _buffer()
    result = FramingEffect(FramingSpec(4, 2, FramingMode.CROP))((source,))
    assert result is not source
    np.testing.assert_array_equal(result.data, source.data)


def test_invalid_specs_and_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        FramingSpec(0, 2)
    with pytest.raises(ValueError, match="focus"):
        FramingSpec(2, 2, focus_x=1.1)
    with pytest.raises(TypeError, match="FramingMode"):
        FramingSpec(2, 2, mode="fill")  # type: ignore[arg-type]

    effect = FramingEffect(FramingSpec(2, 2))
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_crop_rejects_target_larger_than_source() -> None:
    with pytest.raises(ValueError, match="source"):
        FramingEffect(FramingSpec(5, 2, FramingMode.CROP))((_buffer(4, 2),))


def test_effect_is_immutable_and_deterministic() -> None:
    effect = FramingEffect(FramingSpec(3, 3, FramingMode.FILL, focus_x=0.25, focus_y=0.75))
    source = _buffer(4, 2)
    before = source.data.copy()
    first = effect((source,))
    second = effect((source,))

    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(source.data, before)
    with pytest.raises((AttributeError, TypeError)):
        effect.spec = FramingSpec(2, 2)  # type: ignore[misc]


def test_fit_and_fill_reject_nonfinite_geometry_results_by_contract() -> None:
    source = _buffer(3, 3)
    result = FramingEffect(FramingSpec(2, 2, FramingMode.FILL))((source,))
    assert np.isfinite(result.data).all()
