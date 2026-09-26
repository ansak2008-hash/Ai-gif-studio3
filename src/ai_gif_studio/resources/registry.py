from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    provider: str
    vram_bytes: int
    capabilities: frozenset[str]
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("model name must not be empty")
        if not self.provider.strip():
            raise ValueError("model provider must not be empty")
        if self.vram_bytes <= 0:
            raise ValueError("vram_bytes must be positive")


class ModelRegistry:
    """Explicit model metadata registry used by resource admission.

    Models are registered deliberately; there is no implicit fallback to an
    unknown model with an estimated or unlimited memory requirement.
    """

    def __init__(self, models: tuple[ModelSpec, ...] = ()) -> None:
        self._models: dict[str, ModelSpec] = {}
        for model in models:
            self.register(model)

    def register(self, model: ModelSpec) -> None:
        if model.name in self._models:
            raise ValueError(f"model already registered: {model.name}")
        self._models[model.name] = model

    def get(self, name: str) -> ModelSpec:
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(f"unknown model: {name}") from exc

    def require(self, name: str, capability: str | None = None) -> ModelSpec:
        model = self.get(name)
        if not model.enabled:
            raise ValueError(f"model is disabled: {name}")
        if capability is not None and capability not in model.capabilities:
            raise ValueError(f"model {name} does not support capability: {capability}")
        return model

    def all(self) -> tuple[ModelSpec, ...]:
        return tuple(self._models.values())
