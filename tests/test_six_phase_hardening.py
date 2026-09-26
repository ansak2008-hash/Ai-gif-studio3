from __future__ import annotations

import pytest

from ai_gif_studio.application.ai import AICapabilityService
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.motion_engine import pad_expression
from ai_gif_studio.quality_engine import QualityEngine


def test_design_spec_is_bounded_and_versioned():
    spec = DesignSpec(
        motion={"style": "float", "amount": 12},
        layers=[{"type": "border", "color": "#ffffff", "thickness": 4}],
        text={"content": "GIF", "size": 24},
    )
    assert spec.schema_version == 2
    assert spec.canvas == {"width": 320, "height": 320}


def test_design_spec_rejects_unsafe_bounds():
    with pytest.raises(ValueError):
        DesignSpec(text={"content": "x" * 161})


def test_motion_is_deterministic():
    assert pad_expression("float", 8, 6) == pad_expression("float", 8, 6)
    assert pad_expression("float", 8, 6)[0] != pad_expression("pan", 8, 6)[0]


def test_quality_ladder_descends():
    assert QualityEngine().ladder(20) == (20, 16, 12, 10, 8, 6)


@pytest.mark.asyncio
async def test_ai_is_gated_until_verified_provider():
    with pytest.raises(RuntimeError):
        await AICapabilityService().run("background_remove", {})


def test_processing_settings_are_bounded():
    assert ProcessingSettings().max_duration_seconds == 6.0
