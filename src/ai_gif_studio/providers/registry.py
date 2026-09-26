from __future__ import annotations

from .base import AIProvider, ProviderRequest, ProviderResult
from ai_gif_studio.resources import ModelRegistry


class ProviderRegistry:
    """Binds explicit model metadata to a provider implementation."""

    def __init__(self, models: ModelRegistry) -> None:
        self._models = models
        self._providers: dict[str, AIProvider] = {}

    def register(self, model_name: str, provider: AIProvider) -> None:
        model = self._models.require(model_name)
        if provider.capabilities.name != model.provider:
            raise ValueError(
                f"provider mismatch for {model_name}: expected {model.provider}, got {provider.capabilities.name}"
            )
        if not model.capabilities.intersection(provider.capabilities.capabilities):
            raise ValueError(f"provider has no registered capability for model: {model_name}")
        self._providers[model_name] = provider

    def get(self, model_name: str) -> AIProvider:
        self._models.require(model_name)
        try:
            return self._providers[model_name]
        except KeyError as exc:
            raise KeyError(f"no provider registered for model: {model_name}") from exc

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        model = self._models.require(request.model, request.operation)
        provider = self.get(model.name)
        return await provider.execute(request)
