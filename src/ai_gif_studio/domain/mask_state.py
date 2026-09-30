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

    def _replace(self, **changes: object) -> MaskState:
        values = {
            "mask_id": self.mask_id,
            "source_asset_id": self.source_asset_id,
            "enabled": self.enabled,
            "inverted": self.inverted,
            "opacity": self.opacity,
            "feather_radius": self.feather_radius,
            "blur_radius": self.blur_radius,
            "levels_low": self.levels_low,
            "levels_high": self.levels_high,
            "threshold": self.threshold,
        }
        values.update(changes)
        return type(self)(**values)

    def with_enabled(self, enabled: bool) -> MaskState:
        """Return a state with mask application enabled or disabled."""
        return self._replace(enabled=enabled)

    def with_inverted(self, inverted: bool) -> MaskState:
        """Return a state with mask inversion enabled or disabled."""
        return self._replace(inverted=inverted)

    def with_opacity(self, opacity: float) -> MaskState:
        """Return a state with normalized mask opacity."""
        return self._replace(opacity=opacity)

    def with_feather_radius(self, feather_radius: float) -> MaskState:
        """Return a state with the requested feather radius."""
        return self._replace(feather_radius=feather_radius)

    def with_blur_radius(self, blur_radius: float) -> MaskState:
        """Return a state with the requested blur radius."""
        return self._replace(blur_radius=blur_radius)

    def with_levels(self, levels_low: float, levels_high: float) -> MaskState:
        """Return a state with a validated levels interval."""
        return self._replace(levels_low=levels_low, levels_high=levels_high)

    def with_threshold(self, threshold: float | None) -> MaskState:
        """Return a state with thresholding enabled or disabled."""
        return self._replace(threshold=threshold)

    @classmethod
    def from_canonical_json(cls, value: str) -> MaskState:
        if not isinstance(value, str):
            raise TypeError("canonical mask state must be a string")
        try:
            payload = json.loads(value)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("invalid canonical mask state JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("canonical mask state must be an object")
        expected = {
            "mask_id",
            "source_asset_id",
            "enabled",
            "inverted",
            "opacity",
            "feather_radius",
            "blur_radius",
            "levels_low",
            "levels_high",
            "threshold",
        }
        if set(payload) != expected:
            raise ValueError("invalid mask state keys")
        try:
            state = cls(
                UUID(payload["mask_id"]),
                UUID(payload["source_asset_id"]),
                enabled=payload["enabled"],
                inverted=payload["inverted"],
                opacity=payload["opacity"],
                feather_radius=payload["feather_radius"],
                blur_radius=payload["blur_radius"],
                levels_low=payload["levels_low"],
                levels_high=payload["levels_high"],
                threshold=payload["threshold"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid canonical mask state payload") from exc
        if state.canonical_json != value:
            raise ValueError("canonical mask state is not normalized")
        return state

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
