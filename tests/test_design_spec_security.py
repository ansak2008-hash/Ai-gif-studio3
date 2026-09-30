from __future__ import annotations

import pytest

from ai_gif_studio.domain.specs import DesignSpec


@pytest.mark.unit
@pytest.mark.parametrize(
    ("background_key", "value"),
    [
        ("secondary", "#fff,format=rgb"),
        ("accent", "#fff;movie=/etc/passwd"),
    ],
)
def test_background_filter_colors_are_strictly_validated(background_key: str, value: str) -> None:
    with pytest.raises(ValueError):
        DesignSpec(background={background_key: value, "mode": "solid", "color": "#111111"})


@pytest.mark.unit
def test_frame_secondary_color_cannot_inject_filter_options() -> None:
    with pytest.raises(ValueError):
        DesignSpec(frame={"style": "double", "color": "#ffffff", "secondary": "#fff,drawbox"})


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"layers": [{"type": "shape", "color": "#fff", "x": "0:movie=/etc/passwd"}]},
        {"text": {"content": "safe", "x": "0:movie=/etc/passwd"}},
        {"typography": {"content": "safe", "x": "0:movie=/etc/passwd"}},
    ],
)
def test_filter_coordinates_are_numeric_and_bounded(payload: dict) -> None:
    with pytest.raises((TypeError, ValueError)):
        DesignSpec(**payload)


@pytest.mark.unit
def test_background_mode_is_allowlisted() -> None:
    with pytest.raises(ValueError):
        DesignSpec(background={"mode": "movie=/etc/passwd", "color": "#111111"})
