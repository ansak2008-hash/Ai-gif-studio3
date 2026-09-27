import numpy as np
from ai_gif_studio.temporal_engine.depth_field import DepthField

def test_depth_field_is_deterministic():
    a=np.zeros((64,64),dtype=np.float32); a[12:52,12:52]=1
    x=DepthField.from_alpha(a); y=DepthField.from_alpha(a)
    np.testing.assert_array_equal(x.distance_px,y.distance_px)
    np.testing.assert_array_equal(x.height,y.height)
    np.testing.assert_array_equal(x.normals,y.normals)

def test_height_is_zero_outside_and_positive_inside():
    a=np.zeros((32,32),dtype=np.float32); a[8:24,8:24]=1
    d=DepthField.from_alpha(a,bevel_width_px=6)
    assert np.all(d.height[0]==0)
    assert float(d.height[16,16])>0.9

def test_normals_are_unit_length():
    a=np.zeros((32,32),dtype=np.float32); a[8:24,8:24]=1
    n=DepthField.from_alpha(a).normals
    lengths=np.linalg.norm(n,axis=-1)
    assert np.allclose(lengths,1.0,atol=1e-5)
