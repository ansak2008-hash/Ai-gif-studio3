from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.tone_curve import ToneCurve, ToneCurveEffect

pytestmark = pytest.mark.unit


def _buffer() -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray(
            [[[0.0, 0.25, 1.0, 0.4], [2.0, 4.0, 8.0, 0.7]]],
            dtype=np.float32,
        )
    )


def test_tone_curve_interpolates_and_extrapolates_without_clamping() -> None:
    curve = ToneCurve.from_points(((0.0, 0.0), (1.0, 2.0)))
    effect = ToneCurveEffect(curve)
    result = effect((_buffer(),))
    expected_rgb = np.asarray(
        [[[0.0, 0.5, 2.0], [4.0, 8.0, 16.0]]],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.data[..., :3], expected_rgb, rtol=0.0, atol=1e-6)


def test_tone_curve_supports_independent_channels_and_preserves_alpha() -> None:
    red = ToneCurve.from_points(((0.0, 0.0), (1.0, 2.0)))
    green = ToneCurve.from_points(((0.0, 0.0), (1.0, 0.5)))
    blue = ToneCurve.from_points(((0.0, 0.5), (1.0, 1.5)))
    result = ToneCurveEffect(red, green, blue)((_buffer(),))
    expected = np.asarray(
        [[[0.0, 0.125, 1.5, 0.4], [4.0, 2.0, 8.5, 0.7]]],
        dtype=np.float32,
    )
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


@pytest.mark.parametrize(
    "points",
    [
        ((0.0,),),
        ((0.0, 0.0),),
        ((0.0, 0.0), (0.0, 1.0)),
        ((1.0, 0.0), (0.0, 1.0)),
        ((0.0, np.nan), (1.0, 1.0)),
        ((0.0, 0.0), (1.0, np.inf)),
    ],
)
def test_tone_curve_rejects_invalid_points(points: tuple[tuple[float, float], ...]) -> None:
    with pytest.raises((TypeError, ValueError)):
        ToneCurve.from_points(points)


def test_tone_curve_owns_control_points_and_exposes_immutable_storage() -> None:
    points = np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    curve = ToneCurve.from_points(points)
    points[0, 0] = 9.0
    assert curve.points.flags.writeable is False
    np.testing.assert_array_equal(curve.points, np.asarray([[0.0, 0.0], [1.0, 1.0]]))


def test_tone_curve_and_effect_are_structurally_immutable() -> None:
    curve = ToneCurve.from_points(((0.0, 0.0), (1.0, 1.0)))
    effect = ToneCurveEffect(curve)
    with pytest.raises((AttributeError, TypeError)):
        curve.points = np.ones((2, 2))  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        effect.red = curve  # type: ignore[misc]


def test_tone_curve_effect_rejects_wrong_input_count_and_type() -> None:
    effect = ToneCurveEffect(ToneCurve.from_points(((0.0, 0.0), (1.0, 1.0))))
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_tone_curve_effect_does_not_mutate_source_and_is_deterministic() -> None:
    source = _buffer()
    before = source.data.copy()
    effect = ToneCurveEffect(ToneCurve.from_points(((0.0, 0.0), (1.0, 1.5))))
    first = effect((source,))
    second = effect((source,))
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(first.data, second.data)
    assert first is not source


def test_tone_curve_effect_rejects_nonfinite_output_at_render_buffer_boundary() -> None:
    curve = ToneCurve.from_points(((0.0, 0.0), (1.0, 1.0e39)))
    source = RenderBuffer.from_linear_rgba(
        np.asarray([[[1.0, 0.0, 0.0, 1.0]]], dtype=np.float32)
    )
    with pytest.raises(ValueError, match="finite"):
        ToneCurveEffect(curve)((source,))
