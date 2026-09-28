import numpy as np
import pytest

from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.manuscript_renderer import (
    ManuscriptCinematicProfile,
    ManuscriptCinematicRenderer,
)
from ai_gif_studio.temporal_engine.material import Material, material_preset

pytestmark = pytest.mark.unit


def test_profile_has_reference_phases():
    p = ManuscriptCinematicProfile()
    assert (p.reveal_end, p.transform_end, p.macro_end, p.hero_end) == (1.5, 3.5, 7.0, 9.5)
    assert p.canvas == (1280, 720) and p.fps == 30.0


def test_renderer_produces_expected_frame_count_and_rgba():
    asset = ManuscriptAsset(
        np.dstack([
            np.ones((32, 32), np.float32) * 0.7,
            np.ones((32, 32), np.float32) * 0.5,
            np.ones((32, 32), np.float32) * 0.2,
            np.ones((32, 32), np.float32),
        ])
    )
    r = ManuscriptCinematicRenderer()
    frames = r.render_sequence(asset)
    assert len(frames) == 285
    assert frames[0].shape == (720, 1280, 4)
    assert frames[-1].shape == (720, 1280, 4)
    np.testing.assert_array_less(frames[0][..., 3], 1.0 + 1e-7)
    np.testing.assert_array_less(-frames[0][..., 3], 1e-7)


def test_material_presets_are_distinct():
    assert material_preset(Material.CHROME).base_color != material_preset(Material.GOLD).base_color
    assert material_preset(Material.GOLD).base_color != material_preset(Material.PURPLE).base_color
