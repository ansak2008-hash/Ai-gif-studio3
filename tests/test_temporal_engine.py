import numpy as np
import pytest
from ai_gif_studio.temporal_engine import *

def test_reference_timing():
    t=AnimationTimeline(1.48,25)
    assert t.total_frames==37
    assert t.centisecond_delays()==(4,)*37
    assert sum(t.centisecond_delays())==148

def test_true_srgb_transfer_roundtrip():
    x=np.array([0,1,16,64,128,255],dtype=np.uint8)
    assert np.max(np.abs(encode_srgb(linearize_srgb(x))-x))<=1

def test_rotation_modes():
    c=MotionCurve((Keyframe(0,350),Keyframe(1,10)),rotation_mode=RotationMode.SHORTEST,loop_mode=LoopMode.CLAMP)
    assert c.evaluate(.5)==pytest.approx(360)
    p=MotionCurve((Keyframe(0,0),Keyframe(1,0)),rotation_mode=RotationMode.PRESERVE_TURNS,preserve_turns=2,loop_mode=LoopMode.CLAMP)
    assert p.evaluate(.5)==pytest.approx(360)

def test_bezier_rejects_invalid_x():
    with pytest.raises(ValueError): MotionCurve((Keyframe(0,0,(1.2,0,0,1)),Keyframe(1,1)))

def test_affine_is_non_cumulative():
    src=np.zeros((32,32,4),np.float32); src[10:22,10:22,:3]=1; src[10:22,10:22,3]=1
    tr=AffineTransform(translation_px=(3.25,-1.5),scale=(1.02,.98),rotation_deg=7,pivot_px=(16,16))
    a=warp_premultiplied_rgba(src,tr,(64,64)); b=warp_premultiplied_rgba(src,tr,(64,64))
    np.testing.assert_array_equal(a,b)

def test_glint_is_mask_bounded():
    mask=np.zeros((64,64),np.float32); mask[20:44,20:44]=1
    g=gaussian_glint((64,64),GlintParameters(0,8,1),mask,(32,32))
    assert np.all(g[mask==0]==0)

def test_global_palette_is_shared():
    frames=[np.zeros((8,8,3),np.uint8),np.full((8,8,3),255,np.uint8)]
    pal=build_global_palette(frames,2); out=quantize_frames_global(frames,pal)
    assert out[0].palette.palette == out[1].palette.palette
