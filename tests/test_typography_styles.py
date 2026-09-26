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



def test_typography_animation_contract(tmp_path):
    from ai_gif_studio.engines.typography import render_text_filters

    textfile = tmp_path / "overlay.txt"
    textfile.write_text("محمد", encoding="utf-8")
    for animation in ("fade", "slide", "pulse", "shine"):
        filters = render_text_filters(
            {"content": "محمد", "style": "3d", "material": "gold", "animation": animation},
            textfile,
        )
        assert filters
        assert all("drawtext=" in item for item in filters)
    assert "alpha='1-exp(-8*t)'" in render_text_filters({"content": "A", "animation": "fade"}, textfile)[0]
    assert "exp(-6*t)" in render_text_filters({"content": "A", "animation": "slide"}, textfile)[0]
