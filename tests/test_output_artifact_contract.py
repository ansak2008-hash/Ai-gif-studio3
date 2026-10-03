from __future__ import annotations

import io

import pytest
from PIL import Image
from ai_gif_studio.application.gif_analysis import analyze_gif_bytes
from ai_gif_studio.configuration.render import RenderConfiguration
from ai_gif_studio.domain.specs import ProcessingSettings
from ai_gif_studio.quality_engine import QualityEngine
pytestmark = pytest.mark.unit


def _make_contract_gif(*, duration: int = 6000) -> bytes:
    frame = Image.new("RGB", (320, 320), (10, 20, 30))
    output = io.BytesIO()
    frame.save(output, format="GIF", save_all=True, duration=duration, loop=0, optimize=False)
    return output.getvalue()


def test_default_render_configuration_matches_canonical_contract() -> None:
    configuration = RenderConfiguration()
    assert configuration.canvas_width == 320
    assert configuration.canvas_height == 320
    assert configuration.duration_seconds == 6.0
    assert configuration.maximum_output_bytes == 2_400_000
    assert configuration.preferred_fps == 30
    assert configuration.fps_fallback_ladder == (30, 27, 24, 20, 18, 15)
    assert configuration.palette_colors == 256


def test_processing_settings_default_fps_matches_canonical_contract() -> None:
    assert ProcessingSettings().fps == 30


def test_quality_ladder_uses_canonical_descending_ladder() -> None:
    assert QualityEngine().ladder(30) == (30, 27, 24, 20, 18, 15)
    assert QualityEngine().ladder(20) == (20, 18, 15)
    assert QualityEngine().ladder(15) == (15,)


def test_quality_ladder_does_not_increase_explicit_non_ladder_fps() -> None:
    assert QualityEngine().ladder(8) == (8,)


def test_render_configuration_rejects_non_descending_custom_ladder() -> None:
    with pytest.raises(ValueError, match="FPS fallback ladder"):
        RenderConfiguration(preferred_fps=30, fps_fallback_ladder=(30, 30, 24))


def test_produced_gif_artifact_is_measured_against_canonical_contract() -> None:
    payload = _make_contract_gif()
    report = analyze_gif_bytes(payload)
    assert report.width == 320
    assert report.height == 320
    assert report.duration_ms == 6000
    assert report.frame_count == 1
    assert report.max_palette_colors <= 256
    assert report.file_size_bytes <= 2_400_000


def test_produced_gif_artifact_preserves_exact_source_bytes() -> None:
    payload = _make_contract_gif()
    before = bytes(payload)
    report = analyze_gif_bytes(payload)
    assert report.file_size_bytes == len(payload)
    assert payload == before


def test_produced_gif_artifact_observes_256_color_ceiling_at_boundary() -> None:
    frame = Image.new("RGB", (320, 320))
    frame.putdata(
        (
            (index % 256, (index * 3) % 256, (index * 7) % 256)
            for index in range(320 * 320)
        )
    )
    output = io.BytesIO()
    frame.save(output, format="GIF", save_all=True, duration=6000, loop=0, optimize=False)
    report = analyze_gif_bytes(output.getvalue())
    assert report.max_palette_colors == 256


def test_quality_inspection_defaults_match_canonical_output() -> None:
    import inspect

    parameters = inspect.signature(QualityEngine.inspect).parameters
    assert parameters["selected_fps"].default == 30
    assert parameters["expected_duration"].default == 6.0
