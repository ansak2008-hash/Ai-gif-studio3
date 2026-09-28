from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.geometry_transforms import (
    AffineTransformEffect,
    AffineTransformSpec,
    PerspectiveTransformEffect,
    PerspectiveTransformSpec,
)
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer(width: int = 3, height: int = 2) -> RenderBuffer:
    values = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            values[y, x] = (float(x + 1), float(y + 1), 10.0, 1.0)
    return RenderBuffer.from_linear_rgba(values)


def test_affine_identity_preserves_pixels_and_ownership() -> None:
    source = _buffer()
    spec = AffineTransformSpec(
        3,
        2,
        np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64),
    )
    result = AffineTransformEffect(spec)((source,))

    assert result is not source
    np.testing.assert_allclose(result.data, source.data, rtol=0.0, atol=1e-6)


def test_affine_translation_uses_transparent_border() -> None:
    source = _buffer()
    spec = AffineTransformSpec(
        4,
        2,
        np.asarray([[1.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float64),
    )
    result = AffineTransformEffect(spec)((source,))

    np.testing.assert_allclose(result.data[:, 1:], source.data, rtol=0.0, atol=1e-6)
    np.testing.assert_array_equal(
        result.data[:, :1],
        np.zeros((2, 1, 4), dtype=np.float32),
    )


def test_perspective_identity_preserves_pixels_and_ownership() -> None:
    source = _buffer()
    points = np.asarray(
        [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
        dtype=np.float64,
    )
    spec = PerspectiveTransformSpec(3, 2, points, points.copy())
    result = PerspectiveTransformEffect(spec)((source,))

    assert result is not source
    np.testing.assert_allclose(result.data, source.data, rtol=0.0, atol=1e-6)


def test_perspective_maps_four_corners_into_target() -> None:
    source = _buffer()
    source_points = np.asarray(
        [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]],
        dtype=np.float64,
    )
    destination_points = np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=np.float64,
    )
    spec = PerspectiveTransformSpec(2, 2, source_points, destination_points)
    result = PerspectiveTransformEffect(spec)((source,))

    assert result.shape == (2, 2, 4)
    assert np.isfinite(result.data).all()
    assert np.all(result.data[..., 3] <= 1.0)


def test_specs_copy_mutable_arrays_and_effects_are_deterministic() -> None:
    matrix = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    spec = AffineTransformSpec(3, 2, matrix)
    matrix[0, 0] = 7.0
    assert spec.matrix[0, 0] == 1.0
    with pytest.raises(ValueError):
        spec.matrix[0, 0] = 7.0

    source = _buffer()
    before = source.data.copy()
    effect = AffineTransformEffect(spec)
    first = effect((source,))
    second = effect((source,))

    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(source.data, before)


def test_invalid_geometry_and_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        AffineTransformSpec(0, 2, np.eye(2, 3))
    with pytest.raises(ValueError, match="shape"):
        AffineTransformSpec(3, 2, np.eye(3))
    with pytest.raises(ValueError, match="non-degenerate"):
        AffineTransformSpec(3, 2, np.zeros((2, 3)))

    points = np.zeros((4, 2), dtype=np.float64)
    with pytest.raises(ValueError, match="non-degenerate"):
        PerspectiveTransformSpec(3, 2, points, points)

    effect = AffineTransformEffect(
        AffineTransformSpec(3, 2, np.eye(2, 3)),
    )
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]
