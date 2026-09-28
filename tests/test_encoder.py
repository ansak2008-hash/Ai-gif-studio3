import numpy as np
import pytest
from PIL import Image

from ai_gif_studio.temporal_engine.encoder import encode_linear_gif

pytestmark = pytest.mark.integration


def test_encode_linear_gif_converts_linear_rgba_and_writes_valid_gif(tmp_path):
    frame_a = np.zeros((32, 32, 4), dtype=np.float64)
    frame_a[..., 0] = 1.0
    frame_a[..., 3] = 1.0
    frame_b = frame_a.copy()
    frame_b[..., 1] = 0.25

    output = tmp_path / "linear.gif"
    digest = encode_linear_gif(
        [frame_a, frame_b],
        (5, 5),
        output,
    )

    assert output.exists()
    assert len(digest) == 64
    with Image.open(output) as image:
        assert image.format == "GIF"
        assert image.n_frames == 2
        assert image.size == (32, 32)
