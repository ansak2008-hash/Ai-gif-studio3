import numpy as np
import pytest

from ai_gif_studio.engines.advanced_transform import (
    BlendMode,
    CropMode,
    CropSpec,
    affine_transform,
    blend_frames,
    crop_frame,
    perspective_transform,
)


@pytest.mark.unit
def test_fill_crop_honors_focus_and_exact_geometry():
    frame = np.zeros((4, 8, 3), dtype=np.uint8)
    frame[:, 6:, :] = 255
    result = crop_frame(frame, CropSpec(4, 4, CropMode.FILL, focus_x=1.0))
    assert result.shape == (4, 4, 3)
    assert int(result.mean()) == 255


@pytest.mark.unit
def test_fit_crop_has_deterministic_letterbox():
    frame = np.full((4, 8, 3), 120, dtype=np.uint8)
    result = crop_frame(frame, CropSpec(8, 8, CropMode.FIT))
    assert result.shape == (8, 8, 3)
    assert np.all(result[:2] == 0)
    assert np.all(result[2:6] == 120)


@pytest.mark.unit
def test_affine_and_perspective_are_real_warps():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    frame[2:6, 2:6] = 255
    matrix = np.array([[1, 0, 1], [0, 1, 0]], dtype=np.float64)
    shifted = affine_transform(frame, matrix, (8, 8))
    assert shifted[:, 3:7].mean() > frame[:, 3:7].mean()
    points = np.array([[0, 0], [7, 0], [7, 7], [0, 7]], dtype=np.float32)
    destination = np.array([[1, 0], [7, 1], [6, 7], [0, 6]], dtype=np.float32)
    warped = perspective_transform(frame, points, destination, (8, 8))
    assert warped.shape == frame.shape


@pytest.mark.unit
def test_masked_blend_modes_and_alpha_are_bounded():
    base = np.full((4, 4, 4), [100, 100, 100, 255], dtype=np.uint8)
    overlay = np.full((4, 4, 4), [200, 50, 50, 128], dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[:, 2:] = 255
    result = blend_frames(base, overlay, mask, BlendMode.MULTIPLY)
    assert np.array_equal(result[:, :2], base[:, :2])
    assert np.all(result[:, 2:, 3] <= 255)


@pytest.mark.unit
def test_invalid_mask_is_rejected():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="mask"):
        blend_frames(frame, frame, np.zeros((3, 3), dtype=np.uint8))
