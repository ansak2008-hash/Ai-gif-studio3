from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

DESIGN_SPEC_VERSION = 3
PROCESSING_SETTINGS_VERSION = 2
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")


def _validate_color(value: str) -> str:
    if not HEX_COLOR.fullmatch(value):
        raise ValueError("color must be a 3- or 6-digit hex color")
    return value


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = DESIGN_SPEC_VERSION
    canvas: dict[str, int] = Field(default_factory=lambda: {"width": 320, "height": 320})
    crop: dict[str, Any] = Field(default_factory=lambda: {"mode": "smart", "focus": {"x": 0.5, "y": 0.5}})
    background: dict[str, Any] = Field(default_factory=lambda: {"mode": "solid", "color": "#111111"})
    frame: dict[str, Any] = Field(default_factory=lambda: {"style": "rounded", "radius": 24, "color": "#ffffff"})
    motion: dict[str, Any] = Field(default_factory=lambda: {"style": "none", "amount": 8})
    color: dict[str, Any] = Field(default_factory=lambda: {"policy": "adaptive"})
    layers: list[dict[str, Any]] = Field(default_factory=list)
    text: dict[str, Any] | None = None

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value: int) -> int:
        if value not in {1, 2, DESIGN_SPEC_VERSION}:
            raise ValueError(f"unsupported DesignSpec schema version: {value}")
        return DESIGN_SPEC_VERSION

    def model_post_init(self, __context: Any) -> None:
        if self.canvas.get("width") != 320 or self.canvas.get("height") != 320:
            raise ValueError("MVP canvas must be exactly 320x320")
        focus = self.crop.get("focus", {})
        for axis in ("x", "y"):
            value = float(focus.get(axis, 0.5))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"crop focus {axis} must be between 0 and 1")
        _validate_color(str(self.background.get("color", "#111111")))
        _validate_color(str(self.frame.get("color", "#ffffff")))
        motion_style = str(self.motion.get("style", "none"))
        if motion_style not in {"none", "float", "pan"}:
            raise ValueError("motion style must be none, float, or pan")
        if not 0.0 <= float(self.motion.get("amount", 8)) <= 24.0:
            raise ValueError("motion amount must be between 0 and 24 pixels")
        if len(self.layers) > 8:
            raise ValueError("a DesignSpec may contain at most 8 layers")
        for layer in self.layers:
            if str(layer.get("type", "")) not in {"shape", "border", "accent"}:
                raise ValueError("unsupported design layer type")
            _validate_color(str(layer.get("color", "#ffffff")))
            if not 0.0 <= float(layer.get("opacity", 1.0)) <= 1.0:
                raise ValueError("layer opacity must be between 0 and 1")
            if not 1 <= int(layer.get("thickness", 3)) <= 20:
                raise ValueError("layer thickness must be between 1 and 20")
        if self.text is not None:
            if len(str(self.text.get("content", ""))) > 160:
                raise ValueError("text content must be at most 160 characters")
            if not 10 <= int(self.text.get("size", 24)) <= 72:
                raise ValueError("text size must be between 10 and 72")
            _validate_color(str(self.text.get("color", "#ffffff")))

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DesignSpec":
        return cls.model_validate(payload)


class ProcessingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = PROCESSING_SETTINGS_VERSION
    fps: int = Field(20, ge=1, le=30)
    max_duration_seconds: float = Field(6.0, gt=0, le=6.0)
    max_bytes: int = Field(2_400_000, gt=0)
    encoder: str = "ffmpeg-gif"
    palette_colors: int = Field(256, ge=2, le=256)
    resource_timeout_seconds: int = Field(120, gt=0, le=600)
