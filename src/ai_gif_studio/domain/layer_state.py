from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import UUID

from .mask_state import MaskState

DEFAULT_MAX_LAYERS = 256
_TOP_LEVEL_KEYS = frozenset({"layers", "max_layers"})
_LAYER_KEYS = frozenset({"layer_id", "source_asset_id", "opacity", "visible", "blend_mode", "mask"})
_LEGACY_LAYER_KEYS = frozenset({"layer_id", "source_asset_id", "opacity", "visible", "blend_mode"})


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _opacity(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("opacity must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or not 0.0 <= normalized <= 1.0:
        raise ValueError("opacity must be finite and between 0 and 1")
    return normalized


class LayerBlendMode(StrEnum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


def _max_layers(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("max_layers must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class LayerState:
    layer_id: UUID
    source_asset_id: UUID
    opacity: float = 1.0
    visible: bool = True
    blend_mode: LayerBlendMode = LayerBlendMode.NORMAL
    mask: MaskState | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.layer_id, UUID):
            raise TypeError("layer_id must be a UUID")
        if not isinstance(self.source_asset_id, UUID):
            raise TypeError("source_asset_id must be a UUID")
        object.__setattr__(self, "opacity", _opacity(self.opacity))
        if not isinstance(self.visible, bool):
            raise TypeError("visible must be a boolean")
        if not isinstance(self.blend_mode, LayerBlendMode):
            raise TypeError("blend_mode must be a LayerBlendMode")
        if self.mask is not None and not isinstance(self.mask, MaskState):
            raise TypeError("mask must be a MaskState or None")

    @property
    def metadata(self) -> MappingProxyType:
        return MappingProxyType({
            "layer_id": str(self.layer_id),
            "source_asset_id": str(self.source_asset_id),
            "opacity": self.opacity,
            "visible": self.visible,
            "blend_mode": self.blend_mode.value,
            "mask": None if self.mask is None else dict(self.mask.metadata),
        })

    def set_mask(self, layer_id: UUID, mask: MaskState | None) -> LayerStack:
        if mask is not None and not isinstance(mask, MaskState):
            raise TypeError("mask must be a MaskState or None")
        index = self._index(layer_id)
        values = list(self.layers)
        layer = values[index]
        values[index] = LayerState(
            layer.layer_id,
            layer.source_asset_id,
            layer.opacity,
            layer.visible,
            layer.blend_mode,
            mask,
        )
        return LayerStack(tuple(values), max_layers=self.max_layers)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            dict(self.metadata),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True, slots=True)
class LayerStack:
    layers: tuple[LayerState, ...] = ()
    max_layers: int = DEFAULT_MAX_LAYERS

    def __post_init__(self) -> None:
        if not isinstance(self.layers, tuple):
            raise TypeError("layers must be a tuple")
        object.__setattr__(self, "max_layers", _max_layers(self.max_layers))
        if len(self.layers) > self.max_layers:
            raise ValueError("layer count exceeds maximum layer count")
        seen: set[UUID] = set()
        for layer in self.layers:
            if not isinstance(layer, LayerState):
                raise TypeError("layers must contain LayerState values")
            if layer.layer_id in seen:
                raise ValueError("duplicate layer_id")
            seen.add(layer.layer_id)

    def add(self, layer: LayerState) -> LayerStack:
        if not isinstance(layer, LayerState):
            raise TypeError("layer must be a LayerState")
        if layer.layer_id in {item.layer_id for item in self.layers}:
            raise ValueError("duplicate layer_id")
        if len(self.layers) >= self.max_layers:
            raise ValueError("maximum layer count reached")
        return LayerStack(self.layers + (layer,), max_layers=self.max_layers)

    def remove(self, layer_id: UUID) -> LayerStack:
        self._require(layer_id)
        return LayerStack(tuple(layer for layer in self.layers if layer.layer_id != layer_id), max_layers=self.max_layers)

    def move(self, source: int, target: int) -> LayerStack:
        if not isinstance(source, int) or isinstance(source, bool):
            raise TypeError("source index must be an integer")
        if not isinstance(target, int) or isinstance(target, bool):
            raise TypeError("target index must be an integer")
        if not 0 <= source < len(self.layers) or not 0 <= target < len(self.layers):
            raise IndexError("layer index out of range")
        values = list(self.layers)
        layer = values.pop(source)
        values.insert(target, layer)
        return LayerStack(tuple(values), max_layers=self.max_layers)

    def set_visibility(self, layer_id: UUID, visible: bool) -> LayerStack:
        if not isinstance(visible, bool):
            raise TypeError("visible must be a boolean")
        index = self._index(layer_id)
        values = list(self.layers)
        layer = values[index]
        values[index] = LayerState(layer.layer_id, layer.source_asset_id, layer.opacity, visible, layer.blend_mode, layer.mask)
        return LayerStack(tuple(values), max_layers=self.max_layers)

    def set_opacity(self, layer_id: UUID, opacity: float) -> LayerStack:
        index = self._index(layer_id)
        values = list(self.layers)
        layer = values[index]
        values[index] = LayerState(layer.layer_id, layer.source_asset_id, opacity, layer.visible, layer.blend_mode, layer.mask)
        return LayerStack(tuple(values), max_layers=self.max_layers)

    def set_blend_mode(self, layer_id: UUID, blend_mode: LayerBlendMode) -> LayerStack:
        if not isinstance(blend_mode, LayerBlendMode):
            raise TypeError("blend_mode must be a LayerBlendMode")
        index = self._index(layer_id)
        values = list(self.layers)
        layer = values[index]
        values[index] = LayerState(
            layer.layer_id,
            layer.source_asset_id,
            layer.opacity,
            layer.visible,
            blend_mode,
            layer.mask,
        )
        return LayerStack(tuple(values), max_layers=self.max_layers)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            {
                "layers": [dict(layer.metadata) for layer in self.layers],
                "max_layers": self.max_layers,
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_canonical_json(cls, value: str) -> LayerStack:
        if not isinstance(value, str):
            raise TypeError("canonical layer stack must be a string")
        try:
            payload = json.loads(value, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("invalid canonical layer stack JSON") from exc
        if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
            raise ValueError("invalid canonical layer stack keys")
        raw_layers = payload["layers"]
        if not isinstance(raw_layers, list):
            raise ValueError("layers must be a JSON array")
        try:
            max_layers = _max_layers(payload["max_layers"])
            if len(raw_layers) > max_layers:
                raise ValueError("maximum layer count reached")
            layers = tuple(cls._decode_layer(item) for item in raw_layers)
            stack = cls(layers, max_layers=max_layers)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("invalid canonical layer stack payload") from exc
        if stack.canonical_json != value:
            raise ValueError("canonical layer stack is not normalized")
        return stack

    @staticmethod
    def _decode_layer(value: Any) -> LayerState:
        if not isinstance(value, dict):
            raise ValueError("invalid layer keys")
        keys = set(value)
        if keys not in (_LEGACY_LAYER_KEYS, _LAYER_KEYS):
            raise ValueError("invalid layer keys")
        mask = None
        if "mask" in value:
            raw_mask = value["mask"]
            if raw_mask is not None:
                mask = MaskState.from_canonical_json(
                    json.dumps(raw_mask, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
                )
        return LayerState(
            UUID(value["layer_id"]),
            UUID(value["source_asset_id"]),
            opacity=value["opacity"],
            visible=value["visible"],
            blend_mode=LayerBlendMode(value["blend_mode"]),
            mask=mask,
        )

    def _index(self, layer_id: UUID) -> int:
        if not isinstance(layer_id, UUID):
            raise TypeError("layer_id must be a UUID")
        for index, layer in enumerate(self.layers):
            if layer.layer_id == layer_id:
                return index
        raise KeyError(f"unknown layer_id: {layer_id}")

    def _require(self, layer_id: UUID) -> None:
        self._index(layer_id)
