from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ModelRecord:
    model_id: str
    version: str
    exact_source: str
    exact_weight_source: str
    weight_sha256: str | None
    code_license: str
    weights_license: str
    commercial_allowed: bool
    redistribution_allowed: bool
    attribution_required: bool
    gpu_required: bool
    minimum_vram_mb: int | None
    recommended_vram_mb: int | None
    backend: str
    precision: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    verified_at: datetime | None
    verification_source: str | None
