import numpy as np
import pytest

from ai_gif_studio.temporal_engine.camera import CameraState, project_points
from ai_gif_studio.temporal_engine.manuscript_plane import ManuscriptPlane, warp_manuscript

pytestmark = [pytest.mark.unit, pytest.mark.determinism]


def test_camera_projection_bit_identical():
    cam = CameraState(
        (0.5, 1.0, 4.0),
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        45.0,
        16 / 9,
    )
    pts = np.random.default_rng(42).uniform(-2, 2, (100, 3))
    a, _ = project_points(cam.view_projection(), pts, (1920, 1080))
    b, _ = project_points(cam.view_projection(), pts, (1920, 1080))
    np.testing.assert_array_equal(a, b)


def test_manuscript_warp_bit_identical():
    src = np.random.default_rng(0).random((64, 64, 4)).astype(np.float32)
    cam = CameraState(
        (0.0, 0.0, 4.0),
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        45.0,
        16 / 9,
    )
    plane = ManuscriptPlane(
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        1.5,
        1.0,
    )
    a, _ = warp_manuscript(src, cam, plane, (256, 256))
    b, _ = warp_manuscript(src, cam, plane, (256, 256))
    np.testing.assert_array_equal(a, b)
