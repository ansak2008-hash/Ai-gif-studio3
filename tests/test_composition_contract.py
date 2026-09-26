import pytest

from ai_gif_studio.engines.composition import composition_contract, supported_input_aspect


@pytest.mark.unit
@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [(1080, 1920, "9:16"), (1440, 1080, "4:3"), (1080, 1080, "1:1")],
)
def test_supported_aspects_share_fixed_square_canvas(width, height, expected):
    result = composition_contract(width, height)
    assert result["aspect"] == expected
    assert result["canvas"] == {"width": 320, "height": 320}
    assert result["layout"]["canvas"] == {"width": 320, "height": 320}


@pytest.mark.unit
def test_other_aspect_remains_backward_compatible():
    assert supported_input_aspect(1920, 1080) == "other"
    assert composition_contract(1920, 1080)["canvas"] == {"width": 320, "height": 320}
