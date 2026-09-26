from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DESIGN_SPEC_VERSION = 1


class CanvasSpec(BaseModel):
    width: int = Field(default=320, gt=0)
    height: int = Field(default=320, gt=0)


class DesignSpec(BaseModel):
    """Versioned, serializable design intent for a generated GIF."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[DESIGN_SPEC_VERSION] = DESIGN_SPEC_VERSION
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    crop_policy: Literal["center", "smart"] = "smart"
    background_style: Literal["transparent", "solid", "blurred"] = "transparent"
    frame_style: Literal["none", "rounded"] = "none"
    motion_style: Literal["none", "subtle"] = "none"
    color_policy: Literal["source", "adaptive"] = "adaptive"

    @model_validator(mode="before")
    @classmethod
    def migrate(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        version = payload.get("schema_version", 1)
        if version != DESIGN_SPEC_VERSION:
            raise ValueError(f"Unsupported DesignSpec schema version: {version}")
        return {**payload, "schema_version": DESIGN_SPEC_VERSION}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DesignSpec:
        return cls.model_validate(payload)
