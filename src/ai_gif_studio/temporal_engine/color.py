from __future__ import annotations
import numpy as np

def linearize_srgb(rgb: np.ndarray) -> np.ndarray:
    x = np.asarray(rgb, dtype=np.float32) / 255.0 if np.asarray(rgb).dtype != np.float32 or np.max(rgb, initial=0) > 1.0 else np.asarray(rgb, dtype=np.float32)
    return np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4).astype(np.float32)

def encode_srgb(linear: np.ndarray) -> np.ndarray:
    x=np.clip(np.asarray(linear,dtype=np.float32),0,1)
    return (np.where(x<=0.0031308,12.92*x,1.055*np.power(x,1/2.4)-0.055)*255.0+0.5).astype(np.uint8)
