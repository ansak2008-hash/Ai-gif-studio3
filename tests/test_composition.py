from ai_gif_studio.engines.composition import square_layout


def test_square_layout_preserves_focus():
    x = square_layout(1920, 1080, 0.8, 0.5)
    assert x["canvas"] == {"width": 320, "height": 320}
    assert x["crop"]["width"] == 1080
