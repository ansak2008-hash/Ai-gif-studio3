import pytest

from ai_gif_studio.resources import ModelRegistry, ModelSpec


@pytest.mark.unit
def test_registry_exposes_explicit_vram_and_capabilities() -> None:
    registry = ModelRegistry((ModelSpec("demo", "fake", 2 * 1024**3, frozenset({"image"})),))
    model = registry.require("demo", "image")
    assert model.vram_bytes == 2 * 1024**3
    assert model.provider == "fake"


@pytest.mark.unit
def test_unknown_or_unsupported_model_is_not_admitted() -> None:
    registry = ModelRegistry((ModelSpec("demo", "fake", 1, frozenset({"image"})),))
    with pytest.raises(KeyError, match="unknown model"):
        registry.require("missing")
    with pytest.raises(ValueError, match="does not support"):
        registry.require("demo", "video")
