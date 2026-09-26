from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROCESSING_SETTINGS_VERSION = 1


class ProcessingSettings(BaseModel):
    """Versioned operational output settings, independent from design intent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[PROCESSING_SETTINGS_VERSION] = PROCESSING_SETTINGS_VERSION
    max_duration_seconds: float = Field(default=10.0, gt=0, le=60)
    frames_per_second: int = Field(default=15, ge=1, le=60)
    loop_forever: bool = True
    output_format: Literal["gif"] = "gif"

    @model_validator(mode="before")
    @classmethod
    def migrate(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        version = payload.get("schema_version", 1)
        if version != PROCESSING_SETTINGS_VERSION:
            raise ValueError(f"Unsupported ProcessingSettings schema version: {version}")
        return {**payload, "schema_version": PROCESSING_SETTINGS_VERSION}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ProcessingSettings:
        return cls.model_validate(payload)
