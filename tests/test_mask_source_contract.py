from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.mask_processing import (
    mask_from_alpha,
    mask_from_luminance,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer


def buffer(values: list[list[tuple[float, float, float, float]]]) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(np.asarray(values, dtype=np.float32))


def test_mask_from_alpha_extracts_linear_alpha_without_mutating_source() -> None:
    source = buffer([[(0.2, 0.4, 0.6, 0.0), (0.2, 0.4, 0.6, 0.25)]])
    before = source.data.copy()
    result = mask_from_alpha(source)
    np.testing.assert_array_equal(result.data, np.array([[0.0, 0.25]], dtype=np.float32))
    np.testing.assert_array_equal(source.data, before)
    assert result.data.flags.writeable is False


def test_mask_from_luminance_uses_linear_rec709_coefficients() -> None:
    source = buffer([[(1.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 1.0)]])
    result = mask_from_luminance(source)
    np.testing.assert_allclose(
        result.data,
        np.array([[0.2126, 0.7152]], dtype=np.float32),
        rtol=0.0,
        atol=1e-6,
    )


def test_luminance_ignores_alpha() -> None:
    source = buffer([[(1.0, 1.0, 1.0, 0.0)]])
    result = mask_from_luminance(source)
    np.testing.assert_allclose(result.data, np.array([[1.0]], dtype=np.float32))


@pytest.mark.parametrize("value", [object(), None])
def test_mask_sources_reject_non_render_buffers(value: object) -> None:
    with pytest.raises(TypeError):
        mask_from_alpha(value)
    with pytest.raises(TypeError):
        mask_from_luminance(value)


def test_mask_source_results_are_deterministic_and_detached() -> None:
    source = buffer([[(0.5, 0.25, 0.0, 0.5)]])
    first = mask_from_luminance(source)
    second = mask_from_luminance(source)
    np.testing.assert_array_equal(first.data, second.data)
    assert first is not second


def test_luminance_clamps_hdr_linear_rgb_to_mask_range() -> None:
    source = buffer([[(8.0, 0.0, 0.0, 1.0)]])
    result = mask_from_luminance(source)
    np.testing.assert_array_equal(result.data, np.array([[1.0]], dtype=np.float32))
