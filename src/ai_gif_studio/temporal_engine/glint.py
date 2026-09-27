from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class GlintParameters:
    position: float
    width: float=15.0
    intensity: float=1.0
    angle_rad: float=math.radians(30.0)
    tint_linear: tuple[float,float,float]=(1.0,1.0,1.0)

def gaussian_glint(shape: tuple[int,int], params: GlintParameters, alpha_mask: np.ndarray, origin_px: tuple[float,float]) -> np.ndarray:
    if params.width<=0 or params.intensity<0: raise ValueError("invalid glint parameters")
    h,w=shape; y,x=np.ogrid[:h,:w]; ox,oy=origin_px; c=math.cos(params.angle_rad); s=math.sin(params.angle_rad)
    u=(x-ox)*c+(y-oy)*s
    field=np.exp(-0.5*((u-params.position)/params.width)**2).astype(np.float32)*float(params.intensity)
    mask=np.clip(np.asarray(alpha_mask,dtype=np.float32),0,1)
    return field[:,:,None]*np.asarray(params.tint_linear,dtype=np.float32)[None,None,:]*mask[:,:,None]
