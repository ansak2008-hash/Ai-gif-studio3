from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
class CapabilityState(StrEnum): AVAILABLE="available"; PLANNED="planned"
@dataclass(frozen=True, slots=True)
class Capability:
    id:str; state:CapabilityState; requirements:tuple[str,...]=(); description:str=""
CAPABILITIES={x.id:x for x in [
Capability("crop",CapabilityState.AVAILABLE,("ffmpeg",)), Capability("resize",CapabilityState.AVAILABLE,("ffmpeg",)), Capability("compose",CapabilityState.AVAILABLE,("composition-engine",)), Capability("background_remove",CapabilityState.PLANNED,("ai-provider","model-registry")), Capability("background_replace",CapabilityState.PLANNED), Capability("object_remove",CapabilityState.PLANNED), Capability("inpaint",CapabilityState.PLANNED), Capability("upscale",CapabilityState.PLANNED), Capability("interpolate",CapabilityState.PLANNED), Capability("style",CapabilityState.PLANNED), Capability("relight",CapabilityState.PLANNED), Capability("expand",CapabilityState.PLANNED), Capability("text",CapabilityState.PLANNED), Capability("watermark",CapabilityState.PLANNED)]}
