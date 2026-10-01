import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ai_gif_studio.temporal_engine import (
    AffineTransform,
    AnimationTimeline,
    GlintParameters,
    Keyframe,
    LoopMode,
    MotionCurve,
    RotationMode,
    build_global_palette,
    encode_srgb,
    gaussian_glint,
    linearize_srgb,
    quantize_frames_global,
    render_particles,
    warp_premultiplied_rgba,
)
from ai_gif_studio.temporal_engine.particles import ParticleField

pytestmark = pytest.mark.unit


@given(st.integers(min_value=0, max_value=255))
def test_srgb_roundtrip_all_256(v: int):
    x = np.array([v], dtype=np.uint8)
    result = encode_srgb(linearize_srgb(x))
    assert abs(int(result[0]) - v) <= 1


def test_reference_timing():
    t = AnimationTimeline(1.48, 25)
    assert t.total_frames == 37
    assert t.centisecond_delays() == (4,) * 37
    assert sum(t.centisecond_delays()) == 148


def test_rotation_modes():
    c = MotionCurve(
        (Keyframe(0, 350), Keyframe(1, 10)),
        rotation_mode=RotationMode.SHORTEST,
        loop_mode=LoopMode.CLAMP,
    )
    assert c.evaluate(0.5) == pytest.approx(0.0)

    p = MotionCurve(
        (Keyframe(0, 0), Keyframe(1, 0)),
        rotation_mode=RotationMode.PRESERVE_TURNS,
        preserve_turns=2,
        loop_mode=LoopMode.CLAMP,
    )
    assert p.evaluate(0.5) == pytest.approx(360)

    assert c.evaluate(1.0) == pytest.approx(10.0)


def test_rotation_modes_wrap_only_shortest():
    shortest = MotionCurve(
        (Keyframe(0, 10), Keyframe(1, 350)),
        rotation_mode=RotationMode.SHORTEST,
        loop_mode=LoopMode.CLAMP,
    )
    forward = MotionCurve(
        (Keyframe(0, 10), Keyframe(1, 350)),
        rotation_mode=RotationMode.FORWARD,
        loop_mode=LoopMode.CLAMP,
    )
    preserve = MotionCurve(
        (Keyframe(0, 0), Keyframe(1, 0)),
        rotation_mode=RotationMode.PRESERVE_TURNS,
        preserve_turns=2,
        loop_mode=LoopMode.CLAMP,
    )
    assert shortest.evaluate(0.5) == pytest.approx(0.0)
    assert forward.evaluate(0.5) == pytest.approx(180.0)
    assert preserve.evaluate(0.5) == pytest.approx(360.0)


def test_particle_render_is_deterministic_and_bounded():
    field = ParticleField(count=12, seed=7)
    a = render_particles((64, 96), field, 1.25, 1.8)
    b = render_particles((64, 96), field, 1.25, 1.8)
    np.testing.assert_array_equal(a, b)
    assert a.shape == (64, 96, 3)
    assert np.isfinite(a).all()
    assert np.all(a >= 0.0)


def test_bezier_rejects_invalid_x():
    with pytest.raises(ValueError):
        MotionCurve((Keyframe(0, 0, (1.2, 0, 0, 1)), Keyframe(1, 1)))


def test_affine_is_deterministic():
    tr = AffineTransform(
        translation_px=(3.25, -1.5),
        scale=(1.02, 0.98),
        rotation_deg=7,
        pivot_px=(16, 16),
    )
    a = tr.to_matrix()
    b = tr.to_matrix()
    np.testing.assert_array_equal(a, b)


def test_affine_composition_consistency():
    first = AffineTransform(translation_px=(3.0, 0.0), pivot_px=(16, 16))
    second = AffineTransform(translation_px=(0.0, 3.0), rotation_deg=4, pivot_px=(16, 16))
    composed = AffineTransform.compose(first, second)

    a = np.vstack([first.to_matrix(), [0, 0, 1]])
    b = np.vstack([second.to_matrix(), [0, 0, 1]])
    expected = b @ a
    np.testing.assert_allclose(composed.to_matrix(), expected[:2], rtol=0, atol=1e-6)


def test_affine_identity_is_neutral():
    tr = AffineTransform(translation_px=(4, -2), scale=(1.1, 0.9), rotation_deg=8)
    np.testing.assert_allclose(
        AffineTransform.compose(AffineTransform.identity(), tr).to_matrix(),
        tr.to_matrix(),
        atol=1e-6,
    )


def test_warp_is_deterministic():
    src = np.zeros((32, 32, 4), np.float32)
    src[8:24, 8:24, :3] = (0.8, 0.4, 0.2)
    src[8:24, 8:24, 3] = 1
    tr = AffineTransform(translation_px=(2.5, 1.25), rotation_deg=5)
    a = warp_premultiplied_rgba(src, tr, (64, 64))
    b = warp_premultiplied_rgba(src, tr, (64, 64))
    np.testing.assert_array_equal(a, b)


def test_warp_preserves_straight_alpha_contract():
    src = np.zeros((16, 16, 4), np.float32)
    src[4:12, 4:12, :3] = 1
    src[4:12, 4:12, 3] = 0.5
    out = warp_premultiplied_rgba(src, AffineTransform.identity(), (16, 16))
    np.testing.assert_array_less(out[:, :, 3], 1.0 + 1e-7)
    np.testing.assert_array_less(-out[:, :, 3], 1e-7)
    np.testing.assert_array_less(out[:, :, :3], 1.0 + 1e-7)
    np.testing.assert_array_less(-out[:, :, :3], 1e-7)


def test_glint_is_mask_bounded():
    mask = np.zeros((64, 64), np.float32)
    mask[20:44, 20:44] = 1
    g = gaussian_glint((64, 64), GlintParameters(0, 8, 1), mask, (32, 32))
    np.testing.assert_allclose(g[mask == 0], 0.0, atol=1e-7)


def test_glint_angle_rotates_axis():
    mask = np.ones((64, 64), np.float32)
    horizontal = gaussian_glint(
        (64, 64), GlintParameters(0, 4, 1, angle_rad=0), mask, (32, 32)
    )[:, :, 0]
    diagonal = gaussian_glint(
        (64, 64), GlintParameters(0, 4, 1, angle_rad=np.pi / 4), mask, (32, 32)
    )[:, :, 0]
    assert not np.array_equal(horizontal, diagonal)
    assert diagonal[16, 16] != pytest.approx(horizontal[16, 16])


def test_delay_distribution_general():
    for total_cs, n in ((150, 37), (101, 10), (1000, 60), (25, 5)):
        timeline = AnimationTimeline(total_cs / 100.0, n / (total_cs / 100.0))
        delays = timeline.centisecond_delays()
        assert len(delays) == n
        assert sum(delays) == total_cs
        assert all(d >= 1 for d in delays)
        assert max(delays) - min(delays) <= 1


def test_global_palette_is_shared():
    frames = [np.zeros((8, 8, 3), np.uint8), np.full((8, 8, 3), 255, np.uint8)]
    pal = build_global_palette(frames, 2)
    out = quantize_frames_global(frames, pal)
    assert out[0].palette.palette == out[1].palette.palette
    assert out[0].getpixel((0, 0)) != out[1].getpixel((0, 0))


def test_palette_is_deterministic():
    frames = []
    for shift in range(10):
        x = np.linspace(0, 255, 64, dtype=np.uint8)
        r = np.tile(x, (64, 1))
        g = np.roll(r, shift, axis=1)
        b = np.flipud(r)
        frames.append(np.stack([r, g, b], axis=2))
    pal1 = build_global_palette(frames, 256)
    pal2 = build_global_palette(frames, 256)
    np.testing.assert_array_equal(
        np.asarray(pal1.convert("RGB"), dtype=np.uint8),
        np.asarray(pal2.convert("RGB"), dtype=np.uint8),
    )


def test_timeline_rejects_bool_and_non_numeric_constructor_values() -> None:
    with pytest.raises(TypeError):
        AnimationTimeline(True, 10.0)
    with pytest.raises(TypeError):
        AnimationTimeline(1.0, True)
    with pytest.raises(TypeError):
        AnimationTimeline("1.0", 10.0)
    with pytest.raises(TypeError):
        AnimationTimeline(1.0, "10.0")


def test_timeline_timestamps_are_deterministic_monotonic_and_bounded() -> None:
    timeline = AnimationTimeline(1.37, 23.0, loop=False)
    first = timeline.frame_times
    second = timeline.frame_times
    assert first == second
    assert first[0] == 0.0
    assert all(a < b for a, b in zip(first, first[1:]))
    assert all(0.0 <= t < timeline.total_duration_sec for t in first)
    assert timeline.timings() == timeline.timings()


def test_timeline_fractional_frame_boundary_is_stable() -> None:
    timeline = AnimationTimeline(1.0, 10.5)
    assert timeline.total_frames == 10
    assert timeline.frame_times == tuple(
        i / timeline.total_frames for i in range(timeline.total_frames)
    )


def test_timeline_rejects_sub_centisecond_total_duration() -> None:
    with pytest.raises(ValueError, match="too short"):
        AnimationTimeline(0.001, 1.0).centisecond_delays()


def test_timeline_progress_is_deterministic_at_loop_and_clamp_boundaries() -> None:
    looping = AnimationTimeline(2.0, 4.0, loop=True)
    assert looping.progress(2.0) == 0.0
    assert looping.progress(4.5) == 0.25
    non_looping = AnimationTimeline(2.0, 4.0, loop=False)
    assert non_looping.progress(-1.0) == 0.0
    assert non_looping.progress(3.0) == 1.0
