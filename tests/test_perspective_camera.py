import numpy as np
from ai_gif_studio.temporal_engine.camera import CameraState, project_points


def test_identity_projection():
    cam = CameraState((0., 0., 4.), (0., 0., 0.), (0., 1., 0.), 45., 16. / 9.)
    xy, valid = project_points(
        cam.view_projection(), np.array([[0., 0., 0.]]), (1920, 1080)
    )
    assert valid[0]
    np.testing.assert_allclose(xy[0], (960., 540.), atol=1e-6)


def test_pitch_produces_keystone():
    """Pitch must produce non-equal top/bottom edge lengths."""
    cam_flat = CameraState(
        (0., 0., 4.), (0., 0., 0.), (0., 1., 0.), 45., 16. / 9.
    )
    cam_pitch = CameraState(
        (0., -1.5, 4.), (0., 0., 0.), (0., 1., 0.), 45., 16. / 9.
    )
    pts = np.array([
        [-1.5, -1., 0.],
        [1.5, -1., 0.],
        [1.5, 1., 0.],
        [-1.5, 1., 0.],
    ])

    s_flat, _ = project_points(cam_flat.view_projection(), pts, (1920, 1080))
    s_pitch, _ = project_points(cam_pitch.view_projection(), pts, (1920, 1080))

    top_flat = np.linalg.norm(s_flat[1] - s_flat[0])
    bot_flat = np.linalg.norm(s_flat[3] - s_flat[2])
    top_pitch = np.linalg.norm(s_pitch[1] - s_pitch[0])
    bot_pitch = np.linalg.norm(s_pitch[3] - s_pitch[2])

    assert abs(top_flat - bot_flat) < 1.0
    assert abs(top_pitch - bot_pitch) > 50.0, (
        f"Pitch did not produce keystone: top={top_pitch:.1f}, bot={bot_pitch:.1f}"
    )


def test_fov_changes_projection():
    p = np.array([[1., 0., 0.]])
    narrow = CameraState(
        (0., 0., 4.), (0., 0., 0.), (0., 1., 0.), 20., 16. / 9.
    )
    wide = CameraState(
        (0., 0., 4.), (0., 0., 0.), (0., 1., 0.), 90., 16. / 9.
    )
    a = project_points(narrow.view_projection(), p, (1920, 1080))[0][0, 0]
    b = project_points(wide.view_projection(), p, (1920, 1080))[0][0, 0]
    assert abs(a - 960.) > abs(b - 960.)


def test_projection_is_deterministic():
    cam = CameraState(
        (0., 0., 4.), (0., 0., 0.), (0., 1., 0.), 45., 16. / 9.
    )
    pts = np.random.default_rng(0).random((32, 3))
    a = project_points(cam.view_projection(), pts, (1280, 720))
    b = project_points(cam.view_projection(), pts, (1280, 720))
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
