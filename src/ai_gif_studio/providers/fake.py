from __future__ import annotations

from .base import ProviderCapabilities, ProviderRequest, ProviderResult


class FakeAIProvider:
    """Deterministic provider used by CI and staging contract tests."""

    def __init__(self, name: str = "fake") -> None:
        self._capabilities = ProviderCapabilities(name, frozenset({"design"}))

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        if request.operation not in self._capabilities.capabilities:
            raise ValueError(f"unsupported operation: {request.operation}")
        return ProviderResult(
            model=request.model,
            operation=request.operation,
            output={"status": "ok", "provider": self._capabilities.name, "payload": request.payload},
        )
