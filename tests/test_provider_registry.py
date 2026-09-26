import pytest

from ai_gif_studio.providers import FakeAIProvider, ProviderRegistry, ProviderRequest
from ai_gif_studio.resources import ModelRegistry, ModelSpec


@pytest.mark.unit
@pytest.mark.asyncio
async def test_registry_routes_same_contract_to_registered_provider() -> None:
    models = ModelRegistry((ModelSpec("demo", "fake", 2, frozenset({"design"})),))
    providers = ProviderRegistry(models)
    providers.register("demo", FakeAIProvider())
    result = await providers.execute(ProviderRequest("design", {"x": 1}, "demo"))
    assert result.output["provider"] == "fake"


@pytest.mark.unit
def test_registry_rejects_provider_mismatch() -> None:
    models = ModelRegistry((ModelSpec("demo", "expected", 2, frozenset({"design"})),))
    providers = ProviderRegistry(models)
    with pytest.raises(ValueError, match="provider mismatch"):
        providers.register("demo", FakeAIProvider())
