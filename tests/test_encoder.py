
@pytest.mark.parametrize("fps", (30, 27, 24, 20, 18, 15))
def test_encode_gif_preserves_full_canonical_fps_ladder_timing(tmp_path, fps):
    timeline = AnimationTimeline(6.0, fps)
    frames = []
    for index in range(timeline.total_frames):
        frame = np.zeros((32, 32, 3), dtype=np.uint8)
        frame[..., index % 3] = 255
        frames.append(frame)
    output = tmp_path / f"canonical-{fps}.gif"
    encode_gif(frames, timeline.centisecond_delays(), output)
    report = analyze_gif_bytes(output.read_bytes())
    assert report.frame_count == timeline.total_frames
    assert report.duration_ms == 6000
    assert report.effective_fps == pytest.approx(fps, abs=0.01)
    assert report.max_palette_colors <= 256
