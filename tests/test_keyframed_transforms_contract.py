from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.geometry_transforms import AffineTransformSpec
from ai_gif_studio.temporal_engine.keyframed_transforms import (
    AffineTransformKeyframe,
    AffineTransformTrack,
)

pytestmark = pytest.mark.unit


def test_affine_transform_track_samples_parameters_in_declaration_order() -> None:
    track = AffineTransformTrack(
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

    result = track.sample(0.5)

    assert isinstance(result, AffineTransformSpec)
    assert (result.width, result.height) == (320, 240)
    np.testing.assert_allclose(
        result.matrix,
        np.asarray([[1.5, 0.0, 5.0], [0.0, 2.0, 10.0]], dtype=np.float64),
    )
