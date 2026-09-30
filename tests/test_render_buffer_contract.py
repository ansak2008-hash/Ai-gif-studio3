from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import _STORAGE, RenderBuffer

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
        RenderBuffer.from_linear_rgba(negative_rgb)

    invalid_alpha = np.ones((1, 1, 4), dtype=np.float32)
    invalid_alpha[0, 0, 3] = 1.01
    with pytest.raises(ValueError, match="alpha"):
        RenderBuffer.from_linear_rgba(invalid_alpha)

    nan_value = np.zeros((1, 1, 4), dtype=np.float32)
    nan_value[0, 0, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        RenderBuffer.from_linear_rgba(nan_value)


def test_render_buffer_owns_input_and_exposes_read_only_data() -> None:
    source = np.full((1, 1, 4), 0.5, dtype=np.float32)
    source[..., 3] = 1.0
    buffer = RenderBuffer.from_linear_rgba(source)

    source[0, 0, 0] = 0.0
    assert buffer.data[0, 0, 0] == 0.5
    assert buffer.data.flags.writeable is False

    with pytest.raises(ValueError, match="read-only"):
        buffer.data[0, 0, 0] = 0.0


def test_render_buffer_preserves_hdr_rgb() -> None:
    rgba = np.array([[[4.0, 2.0, 0.5, 1.0]]], dtype=np.float32)
    buffer = RenderBuffer.from_linear_rgba(rgba)
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


def test_render_buffer_rejects_writable_view_escalation() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    view = buffer.data
    with pytest.raises(ValueError, match="WRITEABLE"):
        view.setflags(write=True)
    nested = view.view()
    with pytest.raises(ValueError, match="WRITEABLE"):
        nested.setflags(write=True)


def test_render_buffer_rejects_storage_replacement() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    with pytest.raises((AttributeError, TypeError)):
        buffer._rgba_linear = np.zeros((1, 1, 4), dtype=np.float32)


def test_reflective_attribute_replacement_cannot_create_identity_slot() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    with pytest.raises(AttributeError):
        object.__setattr__(buffer, "_identity", object())


def test_raw_ndarray_construction_requires_explicit_color_space_boundary() -> None:
    rgba = np.zeros((1, 1, 4), dtype=np.float32)
    with pytest.raises(TypeError, match="created through"):
        RenderBuffer(rgba)


def test_from_srgb_u8_converts_rgb_and_alpha_explicitly() -> None:
    srgb = np.array([[[128, 64, 255, 128]]], dtype=np.uint8)
    buffer = RenderBuffer.from_srgb_u8(srgb)
    expected_rgb = np.array([[[0.2158605, 0.05126946, 1.0]]], dtype=np.float32)
    expected = np.concatenate(
        [expected_rgb, np.array([[[128 / 255.0]]], dtype=np.float32)],
        axis=-1,
    )
    np.testing.assert_allclose(buffer.data, expected, rtol=0.0, atol=2e-6)


def test_clear_replaces_storage_without_exposing_writable_alias() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    before = buffer.data
    buffer.clear((1.0, 0.0, 0.0, 1.0))
    assert before[0, 0, 0] == 0.0
    with pytest.raises(ValueError, match="WRITEABLE"):
        buffer.data.setflags(write=True)
    np.testing.assert_array_equal(buffer.data, [[[1.0, 0.0, 0.0, 1.0]]])


def test_render_buffer_data_base_is_immutable_bytes() -> None:
    buffer = RenderBuffer.allocate(2, 2)
    data = buffer.data
    assert isinstance(data.base, bytes)
    assert data.flags.writeable is False
    with pytest.raises(ValueError):
        data.setflags(write=True)


def test_render_buffer_internal_storage_cannot_be_escalated() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    raw_bytes, shape, view = _STORAGE[buffer]
    assert shape == buffer.shape
    assert isinstance(raw_bytes, bytes)
    assert view.flags.writeable is False
    with pytest.raises(ValueError):
        view.setflags(write=True)
    with pytest.raises(ValueError):
        view[0, 0, 0] = 1.0


def test_render_buffer_base_mutation_cannot_change_canonical_storage() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    base = buffer.data.base
    assert isinstance(base, bytes)
    with pytest.raises(TypeError):
        base[0] = 1
    np.testing.assert_array_equal(buffer.data, 0.0)


def test_render_buffer_reflection_cannot_create_internal_storage_slot() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    with pytest.raises(AttributeError):
        object.__setattr__(buffer, "_identity", object())
    with pytest.raises(AttributeError):
        object.__delattr__(buffer, "_identity")


def test_render_buffer_memoryview_is_readonly() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    view = memoryview(buffer.data)
    assert view.readonly is True


def test_render_buffer_copy_has_independent_storage() -> None:
    original = RenderBuffer.allocate(1, 1)
    copied = original.copy()
    assert not np.shares_memory(original.data, copied.data)
    np.testing.assert_array_equal(original.data, copied.data)


def test_render_buffer_old_view_survives_clear_without_aliasing_new_storage() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    old_view = buffer.data
    buffer.clear((1.0, 0.0, 0.0, 1.0))
    np.testing.assert_array_equal(old_view, 0.0)
    np.testing.assert_array_equal(buffer.data, [[[1.0, 0.0, 0.0, 1.0]]])
    assert not np.shares_memory(old_view, buffer.data)
