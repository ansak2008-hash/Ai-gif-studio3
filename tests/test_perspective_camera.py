import numpy as np
from ai_gif_studio.temporal_engine.camera import CameraState, project_points


def test_identity_projection():
    cam = CameraState((0.,0.,4.), (0.,0.,0.), (0.,1.,0.), 45., 16./9.)
    xy, valid = project_points(cam.view_projection(), np.array([[0.,0.,0.]]), (1920,1080))
    assert valid[0]
    np.testing.assert_allclose(xy[0], (960.,540.), atol=1e-6)


def test_pitch_changes_projection():
    base = CameraState((0.,0.,4.), (0.,0.,0.), (0.,1.,0.), 45., 16./9.)
    pitch = CameraState((0.,1.5,4.), (0.,0.,0.), (0.,1.,0.), 45., 16./9.)
    pts = np.array([[-1.5,-1.,0.],[1.5,-1.,0.],[1.5,1.,0.],[-1.5,1.,0.]])
    a = project_points(base.view_projection(), pts, (1920,1080))[0]
    b = project_points(pitch.view_projection(), pts, (1920,1080))[0]
    assert not np.allclose(a,b)


def test_fov_changes_projection():
    p = np.array([[1.,0.,0.]])
    narrow = CameraState((0.,0.,4.),(0.,0.,0.),(0.,1.,0.),20.,16./9.)
    wide = CameraState((0.,0.,4.),(0.,0.,0.),(0.,1.,0.),90.,16./9.)
    a = project_points(narrow.view_projection(),p,(1920,1080))[0][0,0]
    b = project_points(wide.view_projection(),p,(1920,1080))[0][0,0]
    assert abs(a-960.) > abs(b-960.)


def test_projection_is_deterministic():
    cam = CameraState((0.,0.,4.),(0.,0.,0.),(0.,1.,0.),45.,16./9.)
    pts = np.random.default_rng(0).random((32,3))
    a = project_points(cam.view_projection(),pts,(1280,720))
    b = project_points(cam.view_projection(),pts,(1280,720))
    np.testing.assert_array_equal(a[0],b[0])
    np.testing.assert_array_equal(a[1],b[1])
