from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.color_effects import GammaEffect, RGBGainEffect
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer() -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[[0.25, 0.5, 1.0, 0.35]]], dtype=np.float32)
    )


def test_gamma_transforms_linear_rgb_and_preserves_alpha() -> None:
    result = GammaEffect(2.0)((_buffer(),))
    expected = np.asarray([[[0.0625, 0.25, 1.0, 0.35]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_gamma_identity_returns_independent_equal_values() -> None:
    source = _buffer()
    result = GammaEffect(1.0)((source,))
    np.testing.assert_array_equal(result.data, source.data)
    assert result is not source


@pytest.mark.parametrize("gamma", [0.0, -1.0, float("nan"), float("inf")])
def test_gamma_rejects_invalid_parameter(gamma: float) -> None:
    with pytest.raises(ValueError, match="gamma"):
        GammaEffect(gamma)


def test_gamma_rejects_wrong_input_count_and_type() -> None:
    effect = GammaEffect(2.0)
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_gamma_does_not_mutate_source_and_is_deterministic() -> None:
    source = _buffer()
    before = source.data.copy()
    first = GammaEffect(0.5)((source,))
    second = GammaEffect(0.5)((source,))
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(first.data, second.data)


def test_rgb_gain_scales_each_channel_and_preserves_alpha() -> None:
    result = RGBGainEffect(2.0, 0.5, 3.0)((_buffer(),))
    expected = np.asarray([[[0.5, 0.25, 3.0, 0.35]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_rgb_gain_identity_returns_independent_equal_values() -> None:
    source = _buffer()
    result = RGBGainEffect(1.0, 1.0, 1.0)((source,))
    np.testing.assert_array_equal(result.data, source.data)
    assert result is not source


@pytest.mark.parametrize(
    ("red", "green", "blue"),
    [
        (-1.0, 1.0, 1.0),
        (1.0, -1.0, 1.0),
        (1.0, 1.0, -1.0),
        (float("nan"), 1.0, 1.0),
        (1.0, float("inf"), 1.0),
    ],
)
def test_rgb_gain_rejects_invalid_parameters(
    red: float, green: float, blue: float
) -> None:
    with pytest.raises(ValueError, match="finite and nonnegative"):
        RGBGainEffect(red, green, blue)


def test_rgb_gain_rejects_wrong_input_count_and_type() -> None:
    effect = RGBGainEffect(1.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_rgb_gain_does_not_mutate_source_and_is_deterministic() -> None:
    source = _buffer()
    before = source.data.copy()
    first = RGBGainEffect(1.5, 0.75, 2.0)((source,))
    second = RGBGainEffect(1.5, 0.75, 2.0)((source,))
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(first.data, second.data)
