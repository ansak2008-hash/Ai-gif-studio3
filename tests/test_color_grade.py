import numpy as np
import pytest

from ai_gif_studio.engines.color_grade import (
    ColorGradeSpec,
    apply_color_grade,
    apply_color_grade_batch,
    build_rgb_lut,
)


@pytest.mark.unit
def test_neutral_grade_is_identity():
    frame = np.arange(4 * 5 * 3, dtype=np.uint8).reshape(4, 5, 3)
    result = apply_color_grade(frame, ColorGradeSpec())
    np.testing.assert_array_equal(result, frame)


@pytest.mark.unit
def test_grade_is_deterministic_and_preserves_alpha():
    frame = np.zeros((8, 8, 4), dtype=np.uint8)
    frame[..., :3] = [40, 120, 220]
    frame[..., 3] = 91
    spec = ColorGradeSpec(contrast=1.3, saturation=0.7, temperature=0.25, tint=-0.1, gamma=1.2)
    first = apply_color_grade(frame, spec)
    second = apply_color_grade(frame, spec)
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first[..., 3], frame[..., 3])


@pytest.mark.unit
def test_lut_is_bounded_and_rgb_distinct():
    lut = build_rgb_lut(ColorGradeSpec(temperature=0.5, tint=-0.5))
    assert lut.shape == (256, 3)
    assert np.all(lut >= 0.0)
    assert np.all(lut <= 255.0)
    assert not np.array_equal(lut[:, 0], lut[:, 2])


@pytest.mark.unit
def test_batch_matches_single_frame_processing():
    frame = np.full((4, 4, 3), 100, dtype=np.uint8)
    spec = ColorGradeSpec(brightness=0.1, saturation=1.5)
    batch = apply_color_grade_batch([frame, frame], spec)
    np.testing.assert_array_equal(batch[0], apply_color_grade(frame, spec))
    np.testing.assert_array_equal(batch[0], batch[1])


@pytest.mark.unit
def test_invalid_grade_is_rejected():
    with pytest.raises(ValueError, match="white_point"):
        ColorGradeSpec(black_point=0.8, white_point=0.7)
    with pytest.raises(ValueError, match="gamma"):
        ColorGradeSpec(gamma=0.01)


@pytest.mark.unit
def test_lut_neutral_mapping_preserves_all_8bit_codes():
    lut = build_rgb_lut(ColorGradeSpec())
    expected = np.arange(256, dtype=np.float64)
    np.testing.assert_array_equal(lut[:, 0], expected)
    np.testing.assert_array_equal(lut[:, 1], expected)
    np.testing.assert_array_equal(lut[:, 2], expected)


@pytest.mark.unit
def test_non_neutral_lut_is_integer_exact_and_bounded():
    frame = np.array([[[17, 83, 241]]], dtype=np.uint8)
    result = apply_color_grade(
        frame,
        ColorGradeSpec(temperature=0.4, tint=-0.2, contrast=1.7, gamma=1.3),
    )
    assert result.dtype == np.uint8
    assert np.all(result >= 0)
    assert np.all(result <= 255)
