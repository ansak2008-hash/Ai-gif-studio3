from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_mask import RenderMask, _MASK_STORAGE

pytestmark = pytest.mark.unit


def test_render_mask_from_array_is_canonical_float32() -> None:
    source = np.array([[0.0, 0.25], [0.5, 1.0]], dtype=np.float64)
    mask = RenderMask.from_array(source)
    assert mask.shape == (2, 2)
    assert mask.dtype == np.dtype(np.float32)
    np.testing.assert_allclose(mask.data, source, rtol=0.0, atol=0.0)


def test_render_mask_owns_input_and_exposes_read_only_data() -> None:
    source = np.full((2, 2), 0.5, dtype=np.float32)
    mask = RenderMask.from_array(source)
    source[0, 0] = 0.0

    assert mask.data[0, 0] == 0.5
    assert mask.data.flags.writeable is False

    with pytest.raises(ValueError, match="read-only"):
        mask.data[0, 0] = 0.0


def test_render_mask_rejects_non_floating_input() -> None:
    with pytest.raises(TypeError, match="floating point"):
        RenderMask.from_array(np.zeros((2, 2), dtype=np.uint8))


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_render_mask_rejects_values_outside_unit_interval(value: float) -> None:
    source = np.zeros((2, 2), dtype=np.float32)
    source[0, 0] = value
    with pytest.raises(ValueError, match="\\[0, 1\\]"):
        RenderMask.from_array(source)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_render_mask_rejects_non_finite_values(value: float) -> None:
    source = np.zeros((2, 2), dtype=np.float32)
    source[0, 0] = value
    with pytest.raises(ValueError, match="finite"):
        RenderMask.from_array(source)


@pytest.mark.parametrize(
    "source",
    [
        np.zeros((2, 2, 1), dtype=np.float32),
        np.zeros((2,), dtype=np.float32),
    ],
)
def test_render_mask_requires_exactly_two_dimensions(source: np.ndarray) -> None:
    with pytest.raises(ValueError, match="HxW"):
        RenderMask.from_array(source)


def test_render_mask_allocate_validates_dimensions_and_value() -> None:
    mask = RenderMask.allocate(3, 2, value=0.25)
    assert mask.shape == (2, 3)
    assert mask.dtype == np.dtype(np.float32)
    np.testing.assert_array_equal(mask.data, 0.25)

    with pytest.raises(ValueError, match="positive"):
        RenderMask.allocate(0, 2)

    with pytest.raises(ValueError, match="positive"):
        RenderMask.allocate(2, 0)

    with pytest.raises(ValueError, match="\\[0, 1\\]"):
        RenderMask.allocate(2, 2, value=1.1)


def test_render_mask_copy_is_independent() -> None:
    original = RenderMask.allocate(2, 2, value=0.25)
    copied = original.copy()

    assert copied is not original
    assert not np.shares_memory(original.data, copied.data)

    with pytest.raises(ValueError):
        copied.data[0, 0] = 1.0

    np.testing.assert_array_equal(original.data, 0.25)
    np.testing.assert_array_equal(copied.data, 0.25)


def test_render_mask_is_deterministic() -> None:
    source = np.array([[0.0, 0.2], [0.7, 1.0]], dtype=np.float64)
    first = RenderMask.from_array(source)
    second = RenderMask.from_array(source)
    np.testing.assert_array_equal(first.data, second.data)


def test_render_mask_data_base_is_immutable_bytes() -> None:
    mask = RenderMask.allocate(2, 2, value=0.5)
    data = mask.data
    assert isinstance(data.base, bytes)
    assert data.flags.writeable is False
    with pytest.raises(ValueError):
        data.setflags(write=True)


def test_render_mask_internal_storage_cannot_be_escalated() -> None:
    mask = RenderMask.allocate(1, 1)
    raw_bytes, shape, view = _MASK_STORAGE[mask]
    assert shape == mask.shape
    assert isinstance(raw_bytes, bytes)
    assert view.flags.writeable is False
    with pytest.raises(ValueError):
        view.setflags(write=True)
    with pytest.raises(ValueError):
        view[0, 0] = 1.0


def test_render_mask_has_no_mutable_mask_slot() -> None:
    mask = RenderMask.allocate(1, 1)
    with pytest.raises(AttributeError):
        _ = mask._mask
    with pytest.raises(AttributeError):
        object.__setattr__(mask, "_mask", np.zeros((1, 1), dtype=np.float32))
