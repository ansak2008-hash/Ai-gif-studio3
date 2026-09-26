from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    name: str
    capabilities: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    operation: str
    payload: dict[str, object]
    model: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    model: str
    operation: str
    output: dict[str, object]


class AIProvider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    async def execute(self, request: ProviderRequest) -> ProviderResult: ...
