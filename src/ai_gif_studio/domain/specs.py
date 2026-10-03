from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .canonical_validation import validate_mapping

DESIGN_SPEC_VERSION = 3
PROCESSING_SETTINGS_VERSION = 2
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")


def _validate_color(value: str, label: str = "color") -> str:
    if not HEX_COLOR.fullmatch(value):
        raise ValueError(f"{label} must be a 3- or 6-digit hex color")
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
    typography: dict[str, Any] | None = None

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value: int) -> int:
        if value not in {1, 2, 3}:
            raise ValueError(f"unsupported DesignSpec schema version: {value}")
        return DESIGN_SPEC_VERSION

    def model_post_init(self, __context: Any) -> None:
        validate_mapping(self.model_dump(mode="python"), context="DesignSpec")
        if self.canvas.get("width") != 320 or self.canvas.get("height") != 320:
            raise ValueError("MVP canvas must be exactly 320x320")
        focus = self.crop.get("focus", {})
        for axis in ("x", "y"):
            value = float(focus.get(axis, 0.5))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"crop focus {axis} must be between 0 and 1")
        _validate_color(str(self.background.get("color", "#111111")), "background color")
        if str(self.background.get("animation", "none")) not in {"none", "pulse", "sweep", "gradient"}:
            raise ValueError("unsupported background animation")
        _validate_color(str(self.frame.get("color", "#ffffff")), "frame color")
        if str(self.frame.get("shape", "rounded")) not in {"rect", "rounded", "rounded-rect", "circle"}:
            raise ValueError("unsupported frame shape")
        if not 0 <= float(self.frame.get("radius", 24)) <= 160:
            raise ValueError("frame radius must be between 0 and 160")
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
            _validate_color(str(layer.get("color", "#ffffff")), "layer color")
            if not 0.0 <= float(layer.get("opacity", 1.0)) <= 1.0:
                raise ValueError("layer opacity must be between 0 and 1")
            if not 1 <= int(layer.get("thickness", 3)) <= 20:
                raise ValueError("layer thickness must be between 1 and 20")
        if self.text is not None:
            if len(str(self.text.get("content", ""))) > 160:
                raise ValueError("text content must be at most 160 characters")
            if not 10 <= int(self.text.get("size", 24)) <= 72:
                raise ValueError("text size must be between 10 and 72")
            _validate_color(str(self.text.get("color", "#ffffff")), "text color")
        if self.typography is not None:
            if len(str(self.typography.get("content", ""))) > 160:
                raise ValueError("typography content must be at most 160 characters")
            if str(self.typography.get("style", "bold")) not in {"flat", "bold", "calligraphy", "3d", "extruded", "gold", "silver", "chrome", "neon"}:
                raise ValueError("unsupported typography style")
            if str(self.typography.get("material", "flat")) not in {"flat", "gold", "silver", "chrome", "neon"}:
                raise ValueError("unsupported typography material")
            if not 10 <= int(self.typography.get("size", 48)) <= 120:
                raise ValueError("typography size must be between 10 and 120")
            if not 0 <= int(self.typography.get("depth", 6)) <= 16:
                raise ValueError("typography depth must be between 0 and 16")
            if str(self.typography.get("animation", "none")) not in {"none", "fade", "slide", "pulse", "shine"}:
                raise ValueError("unsupported typography animation")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DesignSpec:
        return cls.model_validate(payload)


class ProcessingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = PROCESSING_SETTINGS_VERSION
    fps: int = Field(30, ge=1, le=30)
    max_duration_seconds: float = Field(6.0, gt=0, le=6.0)
    max_bytes: int = Field(2_400_000, gt=0, le=2_400_000)
    encoder: str = "ffmpeg-gif"
    palette_colors: int = Field(256, ge=2, le=256)
    resource_timeout_seconds: int = Field(120, gt=0, le=600)
