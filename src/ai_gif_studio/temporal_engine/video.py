from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np


MASTER_SIZE = (320, 320)


class CropStrategy(str, Enum):
    CENTER = "center"
    SMART = "smart"
    FIT = "fit"


@dataclass(frozen=True)
class SubjectState:
    center_x: float = 0.5
    center_y: float = 0.5
    width: float = 1.0
    height: float = 1.0
    confidence: float = 0.0


class OneEuroFilter:
    def __init__(
        self,
        t0: float,
        x0: np.ndarray,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ):
        self.x = np.asarray(x0, dtype=np.float64).copy()
        self.dx = np.zeros_like(self.x)
        self.t = float(t0)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)

    @staticmethod
    def _alpha(dt: float, cutoff: np.ndarray | float) -> np.ndarray | float:
        r = 2 * math.pi * np.asarray(cutoff) * dt
        return r / (r + 1)

    def filter(self, t: float, x: np.ndarray) -> np.ndarray:
        t = float(t)
        if t < self.t:
            raise ValueError("timestamps must be monotonic")
        dt = max(1e-6, t - self.t)
        x = np.asarray(x, dtype=np.float64)
        edx = self.dx + self._alpha(
            dt, np.full_like(x, self.d_cutoff)
        ) * ((x - self.x) / dt - self.dx)
        cutoff = self.min_cutoff + self.beta * np.abs(edx)
        a = self._alpha(dt, cutoff)
        self.x = self.x + a * (x - self.x)
        self.dx = edx
        self.t = t
        return self.x.copy()


class SubjectTracker:
    """Conservative contour-based fallback; it never claims semantic detection."""

    def detect(self, frame_bgr: np.ndarray) -> SubjectState:
        if frame_bgr.ndim != 3:
            raise ValueError("expected BGR frame")
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return SubjectState()
        c = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(c))
        if area < 0.01 * w * h:
            return SubjectState()
        x, y, cw, ch = cv2.boundingRect(c)
        conf = min(1.0, area / (0.25 * w * h))
        return SubjectState((x + cw / 2) / w, (y + ch / 2) / h, cw / w, ch / h, conf)


class CropController:
    def __init__(self, min_cutoff: float = 0.5, beta: float = 0.05):
        self.filter = None
        self.min_cutoff = min_cutoff
        self.beta = beta

    def rect(
        self,
        w: int,
        h: int,
        state: SubjectState,
        t: float,
        strategy: CropStrategy,
    ) -> tuple[int, int, int, int]:
        side = min(w, h)
        cx = (
            0.5
            if strategy is CropStrategy.CENTER or state.confidence < 0.2
            else state.center_x
        )
        cy = (
            0.5
            if strategy is CropStrategy.CENTER or state.confidence < 0.2
            else state.center_y
        )
        raw = np.array([np.clip(cx, 0, 1), np.clip(cy, 0, 1)], np.float64)
        if self.filter is None:
            self.filter = OneEuroFilter(t, raw, self.min_cutoff, self.beta)
            sm = raw
        else:
            sm = self.filter.filter(t, raw)
        x = int(round(np.clip(sm[0] * w - side / 2, 0, w - side)))
        y = int(round(np.clip(sm[1] * h - side / 2, 0, h - side)))
        return x, y, side, side


def normalize_frame(
    frame_bgr: np.ndarray, crop: tuple[int, int, int, int]
) -> np.ndarray:
    x, y, w, h = crop
    cropped = frame_bgr[y : y + h, x : x + w]
    resized = cv2.resize(cropped, MASTER_SIZE, interpolation=cv2.INTER_CUBIC)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    return rgb
