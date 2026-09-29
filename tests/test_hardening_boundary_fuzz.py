from __future__ import annotations

import cv2
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ai_gif_studio.temporal_engine.blend import BlendMode, BlendModeEffect
from ai_gif_studio.temporal_engine.geometry_transforms import (
    AffineTransformSpec,
    PerspectiveTransformSpec,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit

@settings(max_examples=64, derandomize=True, deadline=None)
@given(
    st.integers(min_value=1, max_value=8),
    st.integers(min_value=1, max_value=8),
    st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False, width=32), min_size=1, max_size=64),
)
def test_render_mask_boundary_properties(height: int, width: int, values: list[float]) -> None:
    size = height * width
    data = np.resize(np.asarray(values, dtype=np.float32), size).reshape(height, width)
    mask = RenderMask.from_array(data)
    assert mask.shape == (height, width)
    assert mask.dtype == np.dtype(np.float32)
    assert np.isfinite(mask.data).all()
    assert np.all((mask.data >= 0.0) & (mask.data <= 1.0))
    assert mask.data.flags.writeable is False

@settings(max_examples=64, derandomize=True, deadline=None)
@given(
    st.integers(min_value=1, max_value=32),
    st.integers(min_value=1, max_value=32),
    st.lists(st.floats(min_value=-4.0, max_value=4.0, allow_nan=False, allow_infinity=False, width=32), min_size=6, max_size=6),
)
def test_affine_boundary_properties(width: int, height: int, values: list[float]) -> None:
    matrix = np.asarray(values, dtype=np.float64).reshape(2, 3)
    try:
        spec = AffineTransformSpec(width, height, matrix)
    except (TypeError, ValueError):
        return
    assert spec.matrix.shape == (2, 3)
    assert spec.matrix.dtype == np.dtype(np.float64)
    assert np.isfinite(spec.matrix).all()
    assert spec.matrix.flags.writeable is False

@settings(max_examples=64, derandomize=True, deadline=None)
@given(st.lists(st.floats(min_value=0.0, max_value=16.0, allow_nan=False, allow_infinity=False, width=32), min_size=8, max_size=8))
def test_perspective_boundary_properties(values: list[float]) -> None:
    points = np.asarray(values, dtype=np.float64).reshape(4, 2)
    try:
        spec = PerspectiveTransformSpec(16, 16, points, points + 0.5)
    except (TypeError, ValueError, cv2.error):
        return
    assert spec.source_points.shape == (4, 2)
    assert spec.destination_points.shape == (4, 2)
    assert np.isfinite(spec.source_points).all()
    assert np.isfinite(spec.destination_points).all()
    assert spec.source_points.flags.writeable is False
    assert spec.destination_points.flags.writeable is False


@pytest.mark.parametrize("inputs", [(), (object(),), (object(), object(), object())])
def test_blend_boundary_rejects_wrong_input_count_or_types(inputs: tuple[object, ...]) -> None:
    with pytest.raises((TypeError, ValueError)):
        BlendModeEffect(BlendMode.NORMAL)(inputs)  # type: ignore[arg-type]


def test_blend_boundary_accepts_only_canonical_render_buffers() -> None:
    buffer = RenderBuffer.allocate(1, 1)
    result = BlendModeEffect(BlendMode.NORMAL)((buffer, buffer))
    assert isinstance(result, RenderBuffer)
    assert np.isfinite(result.data).all()
