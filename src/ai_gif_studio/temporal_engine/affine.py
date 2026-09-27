from __future__ import annotations
from dataclasses import dataclass
import math
import cv2
import numpy as np

@dataclass(frozen=True)
class AffineTransform:
    translation_px: tuple[float,float]=(0.0,0.0)
    scale: tuple[float,float]=(1.0,1.0)
    rotation_deg: float=0.0
    pivot_px: tuple[float,float]=(0.0,0.0)
    opacity: float=1.0

    def matrix(self) -> np.ndarray:
        sx,sy=self.scale; tx,ty=self.translation_px; px,py=self.pivot_px
        c=math.cos(math.radians(self.rotation_deg)); s=math.sin(math.radians(self.rotation_deg))
        return np.array([[sx*c,-sy*s,tx+px-sx*c*px+sy*s*py],[sx*s,sy*c,ty+py-sx*s*px-sy*c*py]],dtype=np.float32)

def warp_premultiplied_rgba(rgba_linear: np.ndarray, transform: AffineTransform, out_size: tuple[int,int]) -> np.ndarray:
    src=np.asarray(rgba_linear,dtype=np.float32)
    if src.ndim!=3 or src.shape[2]!=4: raise ValueError("expected RGBA float32")
    a=np.clip(src[:,:,3:4],0,1); premul=np.concatenate([src[:,:,:3]*a, a],axis=2)
    out_w,out_h=out_size
    warped=cv2.warpAffine(premul,transform.matrix(),(out_w,out_h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    alpha=np.clip(warped[:,:,3:4],0,1); rgb=np.divide(warped[:,:,:3],np.maximum(alpha,1e-8),where=alpha>1e-8,out=np.zeros_like(warped[:,:,:3]))
    rgb=np.clip(rgb,0,1); return np.concatenate([rgb,alpha],axis=2)
