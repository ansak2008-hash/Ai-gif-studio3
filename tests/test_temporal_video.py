import numpy as np
import pytest

from ai_gif_studio.temporal_engine.video import (
    CropController,
    CropStrategy,
    OneEuroFilter,
    SubjectState,
)

pytestmark = pytest.mark.unit


def test_one_euro_rejects_time_reversal():
    f = OneEuroFilter(0, np.array([0., 0.]))
    f.filter(0.1, np.array([1., 0.]))
    with pytest.raises(ValueError):
        f.filter(0.05, np.array([0., 0.]))


def test_square_crop_stays_in_bounds():
    c = CropController()
    r = c.rect(
        1920,
        1080,
        SubjectState(.9, .5, .2, .2, .9),
        0,
        CropStrategy.SMART,
    )
    x, y, w, h = r
    assert w == h == 1080
    assert 0 <= x <= 840
    assert 0 <= y <= 0
