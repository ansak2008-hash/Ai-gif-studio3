from __future__ import annotations
from dataclasses import dataclass
import numpy as np

class MaterialPresetStrEnum:
    CHROME = "chrome"
    GOLD = "gold"
    PURPLE = "purple"

@dataclass(frozen=True)
class ManuscriptAsset:
    rgba_linear: np.ndarray
    name: str = "manuscript"

    def __post_init__(self) -> None:
        a = np.asarray(self.rgba_linear)
        if a.ndim != 3 or a.shape[2] != 4:
            raise ValueError("manuscript must be RGBA")
        if not np.issubdtype(a.dtype, np.floating):
            raise TypeError("manuscript RGBA must use floating point linear-light values")
        if a.shape[0] < 1 or a.shape[1] < 1:
            raise ValueError("manuscript dimensions must be positive")

    @property
    def height(self) -> int:
        return int(self.rgba_linear.shape[0])

    @property
    def width(self) -> int:
        return int(self.rgba_linear.shape[1])

    @property
    def alpha(self) -> np.ndarray:
        return np.clip(np.asarray(self.rgba_linear[..., 3], dtype=np.float32), 0.0, 1.0)

    @classmethod
    def from_rgba_u8(cls, rgba: np.ndarray, name: str = "manuscript") -> ManuscriptAsset:
        arr = np.asarray(rgba)
        if arr.ndim != 3 or arr.shape[2] != 4:
            raise ValueError("expected HxWx4 RGBA")
        x = arr.astype(np.float32) / 255.0
        rgb = np.where(x[..., :3] <= 0.04045, x[..., :3] / 12.92,
                       ((x[..., :3] + 0.055) / 1.055) ** 2.4)
        return cls(np.concatenate([rgb, x[..., 3:4]], axis=-1), name)

def alpha_bounds(alpha: np.ndarray, threshold: float = 1e-3) -> tuple[int,int,int,int] | None:
    a = np.asarray(alpha)
    if a.ndim != 2:
        raise ValueError("alpha must be 2D")
    ys, xs = np.nonzero(a > threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
