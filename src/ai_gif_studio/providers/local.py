from __future__ import annotations

from collections.abc import Awaitable, Callable

from .base import ProviderCapabilities, ProviderRequest, ProviderResult


class LocalModelProvider:
    """Adapter for an already-installed local model callable.

    The adapter does not download, select, or implicitly activate a model. A
    deployment supplies the callable explicitly, keeping model licensing and
    lifecycle outside the provider contract.
    """

    def __init__(self, name: str, operations: frozenset[str], runner: Callable[[ProviderRequest], Awaitable[dict[str, object]]]):
        if not name.strip():
            raise ValueError("provider name must not be empty")
        if not operations:
            raise ValueError("at least one operation is required")
        self._capabilities = ProviderCapabilities(name, operations)
        self._runner = runner

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def execute(self, request: ProviderRequest) -> ProviderResult:
        if request.operation not in self._capabilities.capabilities:
            raise ValueError(f"unsupported operation: {request.operation}")
        output = await self._runner(request)
        return ProviderResult(request.model, request.operation, output)
