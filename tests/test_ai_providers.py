import pytest

from ai_gif_studio.providers import FakeAIProvider, LocalModelProvider, ProviderRequest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_provider_matches_common_contract() -> None:
    provider = FakeAIProvider()
    result = await provider.execute(ProviderRequest("design", {"prompt": "test"}, "fake-design"))
    assert result.operation == "design"
    assert result.output["status"] == "ok"
    assert "design" in provider.capabilities.capabilities


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_provider_uses_injected_model_without_downloading() -> None:
    async def runner(request: ProviderRequest) -> dict[str, object]:
        return {"echo": request.payload["prompt"]}

    provider = LocalModelProvider("local-test", frozenset({"design"}), runner)
    result = await provider.execute(ProviderRequest("design", {"prompt": "hello"}, "local-model"))
    assert result.output == {"echo": "hello"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_rejects_unsupported_operation() -> None:
    provider = FakeAIProvider()
    with pytest.raises(ValueError, match="unsupported operation"):
        await provider.execute(ProviderRequest("upscale", {}, "fake"))
