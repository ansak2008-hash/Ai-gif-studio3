import pytest

from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.quality_engine import QualityEngine

pytestmark = pytest.mark.unit


def test_default_render_configuration_matches_output_contract() -> None:
    configuration = RenderConfiguration()
    assert configuration.canvas_width == 320
    assert configuration.canvas_height == 320
    assert configuration.duration_seconds == 6.0
    assert configuration.maximum_output_bytes == 2_400_000
    assert configuration.preferred_fps == 30
    assert configuration.fps_fallback_ladder == (30, 27, 24, 20, 18, 15)
    assert configuration.palette_colors == 256


def test_processing_settings_default_fps_matches_output_contract() -> None:
    assert ProcessingSettings().fps == 30


def test_quality_ladder_uses_canonical_descending_ladder() -> None:
    assert QualityEngine().ladder(30) == (30, 27, 24, 20, 18, 15)


def test_quality_ladder_does_not_increase_explicit_preferred_fps() -> None:
    assert QualityEngine().ladder(20) == (20, 18, 15)
    assert QualityEngine().ladder(15) == (15,)


def test_quality_ladder_preserves_explicit_non_ladder_fps_without_normalization() -> None:
    assert QualityEngine().ladder(8) == (8,)


def test_render_configuration_rejects_non_descending_custom_ladder() -> None:
    with pytest.raises(ValueError, match="FPS fallback ladder"):
        RenderConfiguration(preferred_fps=30, fps_fallback_ladder=(30, 30, 24))
