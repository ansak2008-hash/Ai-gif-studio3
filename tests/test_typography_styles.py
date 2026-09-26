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
    assert len(background_filters({"mode": "luxury"}, Bounds(64, 64, 192, 192))) == 3
    assert len(frame_filters({"style": "gold"})) == 3
