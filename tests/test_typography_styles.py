from ai_gif_studio.domain.specs import DesignSpec
from ai_gif_studio.engines.styles import background_filters, frame_filters
from ai_gif_studio.engines.composition import Bounds
from ai_gif_studio.engines.typography import MATERIALS, STYLES


def test_typography_contract():
    spec = DesignSpec(
        typography={
            "content": "Mohammad",
            "style": "gold",
            "material": "gold",
            "size": 64,
            "depth": 8,
        }
    )
    assert spec.schema_version == 3
    assert "gold" in MATERIALS and "calligraphy" in STYLES


def test_background_and_frames():
    assert len(background_filters({"mode": "luxury"}, Bounds(64, 64, 192, 192))) == 4
    assert len(frame_filters({"style": "gold"})) == 3



def test_real_media_masks_and_animated_styles():
    from ai_gif_studio.engines.composition import Bounds, media_mask_filter
    from ai_gif_studio.engines.styles import animated_background_filters

    circle = media_mask_filter(Bounds(0, 0, 200, 200), "circle", 80)
    rounded = media_mask_filter(Bounds(0, 0, 200, 160), "rounded", 32)
    assert "geq=" in circle and "a='if(" in circle
    assert "geq=" in rounded and "pow(max(abs(X-" in rounded
    sweep = animated_background_filters({"mode": "luxury", "animation": "sweep", "accent": "#f6d36b"}, Bounds(50, 50, 220, 220), 1.0)
    assert any("mod(t/" in item for item in sweep)
