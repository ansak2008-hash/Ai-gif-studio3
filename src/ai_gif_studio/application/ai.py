from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class AIProvider(Protocol):
    async def run(self, workflow: str, inputs: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class AICapability:
    id: str
    state: str
    requirements: tuple[str, ...] = ()


class AICapabilityService:
    capabilities = {
        key: AICapability(key, "planned", ("provider", "verified_weights"))
        for key in (
            "background_remove", "background_replace", "object_remove", "inpaint",
            "upscale", "interpolate", "style", "relight", "expand",
        )
    }

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

    async def run(self, capability: str, inputs: dict[str, Any]) -> dict[str, Any]:
        spec = self.capabilities.get(capability)
        if spec is None:
            raise ValueError(f"unknown AI capability: {capability}")
        if spec.state != "available" or self.provider is None:
            raise RuntimeError(f"AI capability '{capability}' is gated until a verified provider and model weights are configured")
        return await self.provider.run(capability, inputs)
