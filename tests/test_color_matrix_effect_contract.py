from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.color_effects import ColorMatrixEffect
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer() -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[[0.2, 0.4, 0.8, 0.35]]], dtype=np.float32)
    )


def test_color_matrix_applies_affine_rgb_transform_and_preserves_alpha() -> None:
    matrix = np.asarray(
        [
            [2.0, 0.0, 0.0, 0.1],
            [0.0, 0.5, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.2],
        ],
        dtype=np.float32,
    )
    result = ColorMatrixEffect(matrix)((_buffer(),))
    expected = np.asarray([[[0.5, 0.2, 1.0, 0.35]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_color_matrix_identity_is_independent() -> None:
    source = _buffer()
    matrix = np.eye(3, 4, dtype=np.float32)
    result = ColorMatrixEffect(matrix)((source,))
    np.testing.assert_array_equal(result.data, source.data)
    assert result is not source


@pytest.mark.parametrize(
    "matrix",
    [
        np.ones((3, 3), dtype=np.float32),
        np.ones((4, 4), dtype=np.float32),
        np.ones((3, 4), dtype=np.int32),
        np.full((3, 4), np.nan, dtype=np.float32),
        np.full((3, 4), np.inf, dtype=np.float32),
    ],
)
def test_color_matrix_rejects_invalid_matrix(matrix: np.ndarray) -> None:
    with pytest.raises((TypeError, ValueError)):
        ColorMatrixEffect(matrix)


def test_color_matrix_owns_matrix_and_exposes_no_mutable_storage() -> None:
    matrix = np.eye(3, 4, dtype=np.float32)
    effect = ColorMatrixEffect(matrix)
    matrix[0, 0] = 9.0
    result = effect((_buffer(),))
    np.testing.assert_array_equal(result.data, _buffer().data)


def test_color_matrix_rejects_wrong_input_count_and_type() -> None:
    effect = ColorMatrixEffect(np.eye(3, 4, dtype=np.float32))
    with pytest.raises(ValueError, match="exactly one"):
        effect(())
    with pytest.raises(TypeError, match="RenderBuffer"):
        effect((object(),))  # type: ignore[arg-type]


def test_color_matrix_does_not_mutate_source_and_is_deterministic() -> None:
    source = _buffer()
    before = source.data.copy()
    effect = ColorMatrixEffect(
        np.asarray(
            [
                [1.0, 0.1, 0.0, 0.0],
                [0.0, 1.0, 0.2, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
    )
    first = effect((source,))
    second = effect((source,))
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(first.data, second.data)


def test_color_matrix_rejects_nonfinite_or_negative_output_at_canonical_boundary() -> None:
    negative_matrix = np.asarray(
        [
            [-1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    with pytest.raises(ValueError, match="non-negative"):
        ColorMatrixEffect(negative_matrix)((_buffer(),))

    overflow_matrix = np.asarray(
        [
            [1.0e20, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    with pytest.raises(ValueError, match="finite"):
        ColorMatrixEffect(overflow_matrix)((_buffer(),))
