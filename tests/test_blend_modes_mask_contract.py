from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.blend import BlendMode, BlendModeEffect
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit


def _buffers() -> tuple[RenderBuffer, RenderBuffer]:
    destination = RenderBuffer.from_linear_rgba(
        np.asarray([[[0.2, 0.4, 0.8, 0.5]]], dtype=np.float32)
    )
    source = RenderBuffer.from_linear_rgba(
        np.asarray([[[0.6, 0.2, 0.4, 0.75]]], dtype=np.float32)
    )
    return destination, source


def test_normal_mode_matches_source_over() -> None:
    destination, source = _buffers()
    result = BlendModeEffect(BlendMode.NORMAL)((destination, source))
    expected_alpha = 0.75 + 0.5 * (1.0 - 0.75)
    expected_rgb = (
        np.asarray([0.6, 0.2, 0.4]) * 0.75
        + np.asarray([0.2, 0.4, 0.8]) * 0.5 * (1.0 - 0.75)
    ) / expected_alpha
    expected = np.concatenate([expected_rgb, [expected_alpha]]).astype(np.float32)
    np.testing.assert_allclose(result.data[0, 0], expected, rtol=0.0, atol=1e-6)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (BlendMode.MULTIPLY, [0.12, 0.08, 0.32]),
        (BlendMode.SCREEN, [0.68, 0.52, 0.92]),
        (BlendMode.OVERLAY, [0.24, 0.16, 0.76]),
    ],
)
def test_blend_rgb_formulas(mode: BlendMode, expected: list[float]) -> None:
    destination, _ = _buffers()
    opaque_source = RenderBuffer.from_linear_rgba(
        np.asarray([[[0.6, 0.2, 0.4, 1.0]]], dtype=np.float32)
    )
    result = BlendModeEffect(mode)((destination, opaque_source))
    np.testing.assert_allclose(
        result.data[0, 0, :3], expected, rtol=0.0, atol=1e-6
    )


def test_zero_source_alpha_preserves_destination() -> None:
    destination, _ = _buffers()
    transparent_source = RenderBuffer.from_linear_rgba(
        np.asarray([[[0.9, 0.1, 0.7, 0.0]]], dtype=np.float32)
    )
    result = BlendModeEffect(BlendMode.SCREEN)((destination, transparent_source))
    np.testing.assert_array_equal(result.data, destination.data)


def test_opaque_source_replaces_destination_alpha() -> None:
    destination, _ = _buffers()
    opaque_source = RenderBuffer.from_linear_rgba(
        np.asarray([[[0.6, 0.2, 0.4, 1.0]]], dtype=np.float32)
    )
    result = BlendModeEffect(BlendMode.MULTIPLY)((destination, opaque_source))
    assert result.data[0, 0, 3] == 1.0
    np.testing.assert_allclose(
        result.data[0, 0, :3],
        [0.12, 0.08, 0.32],
        rtol=0.0,
        atol=1e-6,
    )


def test_mask_multiplies_source_alpha_only() -> None:
    destination, source = _buffers()
    mask = RenderMask.from_array(np.asarray([[0.5]], dtype=np.float32))
    result = BlendModeEffect(BlendMode.NORMAL, mask=mask)((destination, source))

    masked_alpha = 0.75 * 0.5
    expected_alpha = masked_alpha + 0.5 * (1.0 - masked_alpha)
    expected_rgb = (
        np.asarray([0.6, 0.2, 0.4]) * masked_alpha
        + np.asarray([0.2, 0.4, 0.8]) * 0.5 * (1.0 - masked_alpha)
    ) / expected_alpha
    expected = np.concatenate([expected_rgb, [expected_alpha]]).astype(np.float32)
    np.testing.assert_allclose(result.data[0, 0], expected, rtol=0.0, atol=1e-6)


def test_rejects_wrong_inputs_and_shapes() -> None:
    destination, source = _buffers()
    effect = BlendModeEffect()

    with pytest.raises(ValueError, match="exactly two"):
        effect((destination,))

    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(), source))

    other = RenderBuffer.from_linear_rgba(
        np.zeros((2, 1, 4), dtype=np.float32)
    )
    with pytest.raises(ValueError, match="shapes must match"):
        effect((destination, other))

    mask = RenderMask.allocate(2, 1)
    with pytest.raises(ValueError, match="mask shape"):
        BlendModeEffect(mask=mask)((destination, source))


def test_effect_does_not_mutate_inputs_and_is_deterministic() -> None:
    destination, source = _buffers()
    effect = BlendModeEffect(
        BlendMode.OVERLAY, mask=RenderMask.allocate(1, 1, value=0.8)
    )
    destination_before = destination.data.copy()
    source_before = source.data.copy()

    first = effect((destination, source))
    second = effect((destination, source))

    np.testing.assert_array_equal(destination.data, destination_before)
    np.testing.assert_array_equal(source.data, source_before)
    np.testing.assert_array_equal(first.data, second.data)
    assert first is not destination
    assert first is not source


def test_effect_is_immutable_and_mask_is_owned() -> None:
    points = np.asarray([[0.0]], dtype=np.float32)
    mask = RenderMask.from_array(points)
    effect = BlendModeEffect(mask=mask)

    with pytest.raises((AttributeError, TypeError)):
        effect.mode = BlendMode.SCREEN

    points[0, 0] = 1.0
    assert mask.data[0, 0] == 0.0


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(TypeError):
        BlendModeEffect("unsupported")
