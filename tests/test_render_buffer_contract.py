from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def test_allocate_creates_canonical_float32_linear_rgba() -> None:
    buffer = RenderBuffer.allocate(3, 2)
    assert buffer.shape == (2, 3, 4)
    assert buffer.dtype == np.dtype(np.float32)
    np.testing.assert_array_equal(buffer.data, 0.0)


def test_from_linear_rgba_requires_floating_input() -> None:
    with pytest.raises(TypeError, match="floating point"):
        RenderBuffer.from_linear_rgba(np.zeros((1, 1, 4), dtype=np.uint8))


def test_render_buffer_rejects_invalid_contract_values() -> None:
    negative_rgb = np.zeros((1, 1, 4), dtype=np.float32)
    negative_rgb[0, 0, 0] = -1.0
    with pytest.raises(ValueError, match="non-negative"):
        RenderBuffer(negative_rgb)

    invalid_alpha = np.ones((1, 1, 4), dtype=np.float32)
    invalid_alpha[0, 0, 3] = 1.01
    with pytest.raises(ValueError, match="alpha"):
        RenderBuffer(invalid_alpha)

    nan_value = np.zeros((1, 1, 4), dtype=np.float32)
    nan_value[0, 0, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        RenderBuffer(nan_value)


def test_render_buffer_owns_input_and_exposes_read_only_data() -> None:
    source = np.full((1, 1, 4), 0.5, dtype=np.float32)
    source[..., 3] = 1.0
    buffer = RenderBuffer(source)

    source[0, 0, 0] = 0.0
    assert buffer.data[0, 0, 0] == 0.5
    assert buffer.data.flags.writeable is False

    with pytest.raises(ValueError, match="read-only"):
        buffer.data[0, 0, 0] = 0.0


def test_render_buffer_preserves_hdr_rgb() -> None:
    rgba = np.array([[[4.0, 2.0, 0.5, 1.0]]], dtype=np.float32)
    buffer = RenderBuffer(rgba)
    np.testing.assert_array_equal(buffer.data, rgba)


def test_clear_is_validated_and_does_not_change_representation() -> None:
    buffer = RenderBuffer.allocate(2, 2)
    buffer.clear((2.0, 0.5, 0.25, 0.75))
    assert buffer.dtype == np.dtype(np.float32)
    np.testing.assert_array_equal(buffer.data[0, 0], [2.0, 0.5, 0.25, 0.75])

    with pytest.raises(ValueError, match="alpha"):
        buffer.clear((0.0, 0.0, 0.0, 1.1))


def test_copy_is_independent() -> None:
    original = RenderBuffer.allocate(1, 1)
    original.clear((1.0, 0.0, 0.0, 1.0))
    copied = original.copy()
    copied.clear((0.0, 1.0, 0.0, 1.0))

    np.testing.assert_array_equal(original.data, [[[1.0, 0.0, 0.0, 1.0]]])
    np.testing.assert_array_equal(copied.data, [[[0.0, 1.0, 0.0, 1.0]]])


def test_dimensions_must_be_positive_in_allocate() -> None:
    with pytest.raises(ValueError, match="positive"):
        RenderBuffer.allocate(0, 2)
    with pytest.raises(ValueError, match="positive"):
        RenderBuffer.allocate(2, 0)
