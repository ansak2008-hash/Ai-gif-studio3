from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, strategies as st

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


@st.composite
def _float_rgba_arrays(draw: st.DrawFn) -> np.ndarray:
    height = draw(st.integers(min_value=1, max_value=4))
    width = draw(st.integers(min_value=1, max_value=4))
    values = draw(
        st.lists(
            st.floats(
                width=32,
                allow_nan=True,
                allow_infinity=True,
            ),
            min_size=height * width * 4,
            max_size=height * width * 4,
        )
    )
    return np.asarray(values, dtype=np.float32).reshape(height, width, 4)


@given(_float_rgba_arrays())
def test_render_buffer_property_rejects_invalid_float_values_or_accepts_canonical_values(
    rgba: np.ndarray,
) -> None:
    try:
        buffer = RenderBuffer.from_linear_rgba(rgba)
    except ValueError:
        return

    assert np.isfinite(buffer.data).all()
    assert np.all(buffer.data[..., :3] >= 0.0)
    assert np.all((buffer.data[..., 3] >= 0.0) & (buffer.data[..., 3] <= 1.0))


@given(
    st.integers(min_value=1, max_value=4),
    st.integers(min_value=1, max_value=4),
)
def test_srgb_boundary_accepts_only_uint8_rgba(height: int, width: int) -> None:
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    buffer = RenderBuffer.from_srgb_u8(rgba)
    assert buffer.shape == rgba.shape

    with pytest.raises(TypeError, match="uint8"):
        RenderBuffer.from_srgb_u8(rgba.astype(np.float32))
