from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.compositor import composite_layers, composite_over
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer(rgba: tuple[float, float, float, float]) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(np.array([[rgba]], dtype=np.float32))


def test_composite_over_uses_straight_alpha_and_preserves_hdr_rgb() -> None:
    destination = _buffer((4.0, 0.0, 0.0, 1.0))
    source = _buffer((0.0, 2.0, 0.0, 0.5))

    result = composite_over(destination, source)

    np.testing.assert_allclose(result.data, [[[2.0, 1.0, 0.0, 1.0]]], rtol=0, atol=1e-7)
    np.testing.assert_array_equal(destination.data, [[[4.0, 0.0, 0.0, 1.0]]])
    np.testing.assert_array_equal(source.data, [[[0.0, 2.0, 0.0, 0.5]]])


def test_composite_over_handles_transparent_source() -> None:
    destination = _buffer((1.0, 2.0, 3.0, 0.75))
    source = _buffer((9.0, 8.0, 7.0, 0.0))

    result = composite_over(destination, source)

    np.testing.assert_allclose(result.data, destination.data, rtol=0, atol=1e-7)


def test_composite_over_handles_transparent_destination() -> None:
    destination = _buffer((0.0, 0.0, 0.0, 0.0))
    source = _buffer((3.0, 2.0, 1.0, 0.25))

    result = composite_over(destination, source)

    np.testing.assert_allclose(result.data, [[[3.0, 2.0, 1.0, 0.25]]], rtol=0, atol=1e-7)


def test_composite_over_normalizes_rgb_for_partial_output_alpha() -> None:
    destination = _buffer((2.0, 0.0, 0.0, 0.25))
    source = _buffer((0.0, 4.0, 0.0, 0.25))

    result = composite_over(destination, source)

    np.testing.assert_allclose(
        result.data,
        [[[0.85714286, 2.28571429, 0.0, 0.4375]]],
        rtol=0,
        atol=1e-6,
    )


def test_composite_over_handles_fully_transparent_inputs() -> None:
    destination = _buffer((5.0, 6.0, 7.0, 0.0))
    source = _buffer((9.0, 8.0, 7.0, 0.0))

    result = composite_over(destination, source)

    np.testing.assert_allclose(result.data, [[[0.0, 0.0, 0.0, 0.0]]], rtol=0, atol=1e-7)


def test_composite_over_requires_matching_shapes() -> None:
    destination = RenderBuffer.allocate(2, 2)
    source = RenderBuffer.allocate(1, 2)

    with pytest.raises(ValueError, match="shapes must match"):
        composite_over(destination, source)


def test_composite_over_rejects_non_render_buffers() -> None:
    buffer = RenderBuffer.allocate(1, 1)

    with pytest.raises(TypeError, match="destination"):
        composite_over(np.zeros((1, 1, 4), dtype=np.float32), buffer)

    with pytest.raises(TypeError, match="source"):
        composite_over(buffer, np.zeros((1, 1, 4), dtype=np.float32))


def test_composite_layers_is_ordered_back_to_front() -> None:
    background = _buffer((0.0, 0.0, 1.0, 1.0))
    middle = _buffer((1.0, 0.0, 0.0, 0.5))
    foreground = _buffer((0.0, 1.0, 0.0, 0.5))

    result = composite_layers([background, middle, foreground])

    np.testing.assert_allclose(
        result.data,
        [[[0.25, 0.5, 0.25, 1.0]]],
        rtol=0,
        atol=1e-7,
    )


def test_composite_layers_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError, match="at least one"):
        composite_layers([])
