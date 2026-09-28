from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.geometry_transforms import AffineTransformSpec
from ai_gif_studio.temporal_engine.keyframed_transforms import (
    AffineTransformKeyframe,
    AffineTransformTrack,
)

pytestmark = pytest.mark.unit


def _track() -> AffineTransformTrack:
    return AffineTransformTrack(
        width=320,
        height=240,
        keyframes=(
            AffineTransformKeyframe(
                0.0,
                np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
            ),
            AffineTransformKeyframe(
                1.0,
                np.asarray([[2.0, 0.0, 10.0], [0.0, 3.0, 20.0]]),
            ),
        ),
    )


def test_affine_transform_track_samples_parameters_in_declaration_order() -> None:
    result = _track().sample(0.5)

    assert isinstance(result, AffineTransformSpec)
    assert (result.width, result.height) == (320, 240)
    np.testing.assert_allclose(
        result.matrix,
        np.asarray([[1.5, 0.0, 5.0], [0.0, 2.0, 10.0]], dtype=np.float64),
    )


def test_affine_transform_track_clamps_endpoints() -> None:
    track = _track()
    np.testing.assert_array_equal(track.sample(-1.0).matrix, track.keyframes[0].matrix)
    np.testing.assert_array_equal(track.sample(2.0).matrix, track.keyframes[-1].matrix)


def test_affine_transform_track_owns_mutable_configuration() -> None:
    matrix = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    keyframe = AffineTransformKeyframe(0.0, matrix)
    matrix[...] = 7.0
    assert np.allclose(
        keyframe.matrix,
        np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
    )
    assert keyframe.matrix.flags.writeable is False


def test_affine_transform_track_normalizes_mutable_keyframe_collection() -> None:
    keyframes = [
        AffineTransformKeyframe(
            0.0,
            np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        ),
        AffineTransformKeyframe(
            1.0,
            np.asarray([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0]]),
        ),
    ]
    track = AffineTransformTrack(width=10, height=10, keyframes=keyframes)
    keyframes.append(
        AffineTransformKeyframe(
            2.0,
            np.asarray([[3.0, 0.0, 0.0], [0.0, 3.0, 0.0]]),
        )
    )
    assert len(track.keyframes) == 2
    assert isinstance(track.keyframes, tuple)


def test_affine_transform_track_rejects_invalid_contract() -> None:
    valid = _track().keyframes
    with pytest.raises(ValueError, match="at least two"):
        AffineTransformTrack(width=10, height=10, keyframes=(valid[0],))
    with pytest.raises(ValueError, match="strictly increasing"):
        AffineTransformTrack(width=10, height=10, keyframes=(valid[1], valid[0]))
    with pytest.raises(ValueError, match="finite"):
        _track().sample(float("nan"))
