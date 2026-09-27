from __future__ import annotations

import cv2
import numpy as np

def edge_reveal(alpha: np.ndarray, progress: float, softness: float = 7.0,
                intensity: float = 2.0) -> np.ndarray:
    a = np.clip(np.asarray(alpha,dtype=np.float32),0,1)
    gx = cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.magnitude(gx,gy)
    edge = cv2.GaussianBlur(edge,(0,0),max(0.1,float(softness)))
    # Reveal is a temporal gate, not a destructive alpha operation.
    gate = 1.0 - max(0.0,min(1.0,float(progress)))
    return edge * gate * float(intensity)

def bloom(image: np.ndarray, threshold: float = 1.0, sigma: float = 6.0,
          strength: float = 0.35) -> np.ndarray:
    x = np.asarray(image,dtype=np.float32)
    bright = np.maximum(x-threshold,0.0)
    return x + cv2.GaussianBlur(bright,(0,0),max(0.1,float(sigma))) * float(strength)
