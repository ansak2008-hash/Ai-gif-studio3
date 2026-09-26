from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityState(StrEnum):
    AVAILABLE = "available"
    PLANNED = "planned"


@dataclass(frozen=True, slots=True)
class Capability:
    id: str
    state: CapabilityState
    requirements: tuple[str, ...] = ()
    description: str = ""


CAPABILITIES = {
    item.id: item for item in [
        Capability("crop", CapabilityState.AVAILABLE, ("ffmpeg",), "Deterministic crop to 320x320."),
        Capability("resize", CapabilityState.AVAILABLE, ("ffmpeg",)),
        Capability("compose", CapabilityState.AVAILABLE, ("composition-engine",)),
        Capability("motion", CapabilityState.AVAILABLE, ("ffmpeg",), "Bounded float/pan motion."),
        Capability("layers", CapabilityState.AVAILABLE, ("ffmpeg",), "Bounded decorative layers."),
        Capability("text", CapabilityState.AVAILABLE, ("ffmpeg-drawtext",), "Bounded text overlay."),
        Capability("typography", CapabilityState.AVAILABLE, ("ffmpeg-drawtext",), "Arabic/Latin typography with bounded materials and depth."),
        Capability("frames", CapabilityState.AVAILABLE, ("ffmpeg-drawbox",), "Deterministic decorative frame presets."),
        Capability("backgrounds", CapabilityState.AVAILABLE, ("ffmpeg",), "Deterministic background presets."),
        Capability("presets", CapabilityState.AVAILABLE, ("design-spec-v3",), "Eight deterministic, allowlisted design presets."),
        Capability("quality_gate", CapabilityState.AVAILABLE, ("ffmpeg",), "Adaptive FPS and output validation."),
        *[
            Capability(name, CapabilityState.PLANNED, ("ai-provider", "verified-weights"))
            for name in (
                "background_remove", "background_replace", "object_remove", "inpaint",
                "upscale", "interpolate", "style", "relight", "expand",
            )
        ],
    ]
}
