from __future__ import annotations

import json
import math
from dataclasses import dataclass
from uuid import UUID

MAX_MASK_FEATHER_RADIUS = 4096.0
MAX_MASK_BLUR_RADIUS = 4096.0


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return normalized


def _radius(value: float, name: str, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 <= normalized <= maximum:
        raise ValueError(f"{name} must be finite and between 0 and {maximum:g}")
    return normalized


@dataclass(frozen=True, slots=True)
class MaskState:
    """Immutable persistent layer-mask state.

    Pixel storage is referenced by source_asset_id and is never embedded in
    project JSON. Rendering materializes that asset as a RenderMask.
    """

    mask_id: UUID
    source_asset_id: UUID
    enabled: bool = True
    inverted: bool = False
    opacity: float = 1.0
    feather_radius: float = 0.0
    blur_radius: float = 0.0
    levels_low: float = 0.0
    levels_high: float = 1.0
    threshold: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mask_id, UUID):
            raise TypeError("mask_id must be a UUID")
        if not isinstance(self.source_asset_id, UUID):
            raise TypeError("source_asset_id must be a UUID")
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a boolean")
        if not isinstance(self.inverted, bool):
            raise TypeError("inverted must be a boolean")
        object.__setattr__(self, "opacity", _unit_interval(self.opacity, "opacity"))
        object.__setattr__(
            self,
            "feather_radius",
            _radius(self.feather_radius, "feather_radius", MAX_MASK_FEATHER_RADIUS),
        )
        object.__setattr__(
            self,
            "blur_radius",
            _radius(self.blur_radius, "blur_radius", MAX_MASK_BLUR_RADIUS),
        )
        low = _unit_interval(self.levels_low, "levels_low")
        high = _unit_interval(self.levels_high, "levels_high")
        if low >= high:
            raise ValueError("levels_low must be less than levels_high")
        object.__setattr__(self, "levels_low", low)
        object.__setattr__(self, "levels_high", high)
        if self.threshold is not None:
            object.__setattr__(self, "threshold", _unit_interval(self.threshold, "threshold"))

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "mask_id": str(self.mask_id),
            "source_asset_id": str(self.source_asset_id),
            "enabled": self.enabled,
            "inverted": self.inverted,
            "opacity": self.opacity,
            "feather_radius": self.feather_radius,
            "blur_radius": self.blur_radius,
            "levels_low": self.levels_low,
            "levels_high": self.levels_high,
            "threshold": self.threshold,
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.metadata,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
