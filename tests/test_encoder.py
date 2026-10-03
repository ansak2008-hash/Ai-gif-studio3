import numpy as np
import pytest
from PIL import Image

from ai_gif_studio.application.gif_analysis import analyze_gif_bytes
from ai_gif_studio.temporal_engine.encoder import encode_gif, encode_linear_gif
from ai_gif_studio.temporal_engine.timeline import AnimationTimeline

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


def test_encode_gif_preserves_canonical_six_second_30fps_timing(tmp_path):
    frames = []
    for index in range(180):
        frame = np.zeros((320, 320, 3), dtype=np.uint8)
        frame[..., index % 3] = 255
        frames.append(frame)

    output = tmp_path / "canonical.gif"
    encode_gif(frames, AnimationTimeline(6.0, 30).centisecond_delays(), output)

    report = analyze_gif_bytes(output.read_bytes())
    assert report.width == 320
    assert report.height == 320
    assert report.frame_count == 180
    assert report.duration_ms == 6000
    assert report.effective_fps == pytest.approx(30.0)
    assert report.max_palette_colors <= 256
    assert report.duration_min_ms >= 30
    assert report.duration_max_ms <= 40

def test_encode_gif_preserves_canonical_fps_ladder_timing(tmp_path):
    for fps in (30, 27, 24, 20, 18, 15):
        frame_count = AnimationTimeline(6.0, fps).total_frames
        frames = []
        for index in range(frame_count):
            frame = np.zeros((320, 320, 3), dtype=np.uint8)
            y = index % 300
            x = (index * 7) % 300
            frame[y : y + 20, x : x + 20] = 255
            frames.append(frame)

        output = tmp_path / f"canonical-{fps}.gif"
        encode_gif(frames, AnimationTimeline(6.0, fps).centisecond_delays(), output)
        report = analyze_gif_bytes(output.read_bytes())

        assert report.width == 320
        assert report.height == 320
        assert report.frame_count == frame_count
        assert report.duration_ms == 6000
        assert report.effective_fps == pytest.approx(fps, abs=0.05)
        assert report.max_palette_colors <= 256
