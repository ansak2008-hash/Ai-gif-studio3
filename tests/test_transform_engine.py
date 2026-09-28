import numpy as np
import pytest

from ai_gif_studio.engines.transform import (
    TransformOp,
    TransformSpec,
    TransformStep,
    apply_transform,
    apply_transform_batch,
)


@pytest.mark.unit
def test_transform_chain_is_deterministic_and_preserves_alpha():
    frame = np.zeros((8, 10, 4), dtype=np.uint8)
    frame[:, :, :3] = [40, 80, 120]
    frame[:, :, 3] = 77
    spec = TransformSpec(
        (
            TransformStep(TransformOp.BRIGHTNESS, 20),
            TransformStep(TransformOp.CONTRAST, 1.2),
            TransformStep(TransformOp.SATURATION, 0.5),
            TransformStep(TransformOp.VIGNETTE, 0.4),
        )
    )
    first = apply_transform(frame, spec)
    second = apply_transform(frame, spec)
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first[:, :, 3], frame[:, :, 3])


@pytest.mark.unit
def test_geometry_and_batch_are_real_transformations():
    frame = np.arange(3 * 4 * 3, dtype=np.uint8).reshape(3, 4, 3)
    spec = TransformSpec(
        (
            TransformStep(TransformOp.FLIP_H),
            TransformStep(TransformOp.ROTATE_90, 1),
            TransformStep(TransformOp.RESIZE, (8, 6)),
        )
    )
    result = apply_transform(frame, spec)
    batch = apply_transform_batch([frame, frame], spec)
    assert result.shape == (6, 8, 3)
    np.testing.assert_array_equal(result, batch[0])
    np.testing.assert_array_equal(batch[0], batch[1])


@pytest.mark.unit
def test_invalid_transform_bounds_are_rejected():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="contrast"):
        apply_transform(frame, TransformSpec((TransformStep(TransformOp.CONTRAST, 5),)))
    with pytest.raises(ValueError, match="pixelate"):
        apply_transform(frame, TransformSpec((TransformStep(TransformOp.PIXELATE, 1),)))
    with pytest.raises(ValueError, match="shape"):
        apply_transform(np.zeros((4, 4), dtype=np.uint8), TransformSpec())


@pytest.mark.unit
def test_posterize_and_grayscale_are_bounded():
    frame = np.array([[[10, 80, 220], [255, 40, 90]]], dtype=np.uint8)
    gray = apply_transform(frame, TransformSpec((TransformStep(TransformOp.GRAYSCALE),)))
    poster = apply_transform(frame, TransformSpec((TransformStep(TransformOp.POSTERIZE, 4),)))
    assert gray.dtype == np.uint8
    assert poster.dtype == np.uint8
    assert int(poster.min()) >= 0 and int(poster.max()) <= 255
    assert np.array_equal(gray[:, :, 0], gray[:, :, 1])
    assert np.array_equal(gray[:, :, 1], gray[:, :, 2])
