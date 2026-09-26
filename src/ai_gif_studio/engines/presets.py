from __future__ import annotations

from copy import deepcopy
from typing import Any

from ai_gif_studio.domain.specs import DesignSpec

PRESETS: dict[str, dict[str, Any]] = {
    "luxury_gold": {"background": {"mode": "luxury", "color": "#08090c", "secondary": "#11131a"}, "frame": {"style": "gold", "color": "#f6d36b"}, "typography": {"style": "gold", "material": "gold", "size": 64, "depth": 8}},
    "silver_chrome": {"background": {"mode": "duotone", "color": "#11151a", "secondary": "#dce3e9"}, "frame": {"style": "chrome", "color": "#dce3e9"}, "typography": {"style": "chrome", "material": "chrome", "size": 64, "depth": 7}},
    "arabic_calligraphy": {"background": {"mode": "luxury", "color": "#08090c", "secondary": "#11131a"}, "frame": {"style": "royal", "color": "#f6d36b", "secondary": "#6b4508"}, "typography": {"style": "calligraphy", "material": "gold", "size": 68, "depth": 5, "script": "arabic"}},
    "3d_name": {"background": {"mode": "solid", "color": "#101820"}, "frame": {"style": "simple", "color": "#ffffff"}, "typography": {"style": "3d", "material": "silver", "size": 64, "depth": 10}},
    "royal": {"background": {"mode": "luxury", "color": "#160b24", "secondary": "#281044"}, "frame": {"style": "royal", "color": "#f6d36b", "secondary": "#fff0a6"}, "typography": {"style": "bold", "material": "gold", "size": 62, "depth": 6}},
    "neon": {"background": {"mode": "duotone", "color": "#08090c", "secondary": "#151b2b"}, "frame": {"style": "neon"}, "typography": {"style": "neon", "material": "neon", "size": 60, "depth": 4}},
    "minimal": {"background": {"mode": "solid", "color": "#111111"}, "frame": {"style": "simple", "color": "#ffffff", "thickness": 2}, "typography": {"style": "flat", "material": "flat", "size": 54, "depth": 0}},
    "dark_luxury": {"background": {"mode": "luxury", "color": "#050507", "secondary": "#0d0f14"}, "frame": {"style": "silver", "color": "#dce3e9"}, "typography": {"style": "chrome", "material": "chrome", "size": 60, "depth": 6}},
}


def list_presets() -> tuple[str, ...]:
    return tuple(PRESETS)


def build_design_spec(name: str, overrides: dict[str, Any] | None = None) -> DesignSpec:
    key = str(name).strip().lower()
    if key not in PRESETS:
        raise ValueError(f"unknown design preset: {name}")
    payload = deepcopy(PRESETS[key])
    for section, values in (overrides or {}).items():
        if section not in {"canvas", "crop", "background", "frame", "motion", "color", "layers", "text", "typography"}:
            raise ValueError(f"unsupported preset override section: {section}")
        if section in {"background", "frame", "motion", "color", "typography", "crop", "canvas"}:
            if not isinstance(values, dict):
                raise ValueError(f"preset override {section} must be an object")
            payload.setdefault(section, {}).update(values)
        else:
            payload[section] = values
    return DesignSpec(**payload)
