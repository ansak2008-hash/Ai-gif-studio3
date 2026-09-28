import numpy as np
import pytest

from ai_gif_studio.temporal_engine.color_export import (
    ExportColorSpec,
    linear_rgba_to_srgb_rgb,
    tone_map_reinhard,
)

pytestmark = pytest.mark.unit


def test_linear_rgba_export_composites_before_srgb_encoding():
    rgba = np.array(
        [[[1.0, 0.0, 0.0, 0.5], [0.0, 0.0, 0.0, 0.0]]],
        dtype=np.float64,
    )
    result = linear_rgba_to_srgb_rgb(
        rgba,
        ExportColorSpec(background_linear=(1.0, 1.0, 1.0)),
    )
    assert result.dtype == np.uint8
    np.testing.assert_array_equal(result[0, 0], [255, 188, 188])
    np.testing.assert_array_equal(result[0, 1], [255, 255, 255])


def test_reinhard_tone_mapping_is_bounded_and_monotone():
    rgb = np.array([[[0.0, 0.5, 1.0], [2.0, 10.0, 100.0]]], dtype=np.float64)
    mapped = tone_map_reinhard(rgb)
    assert mapped.dtype == np.float64
    assert np.all(mapped >= 0.0)
    assert np.all(mapped <= 1.0)
    assert np.all(np.diff(mapped[0, :, 2]) > 0.0)


def test_export_rejects_invalid_color_contract():
    with pytest.raises(ValueError, match="tone_mapping"):
        ExportColorSpec(tone_mapping="filmic")
    with pytest.raises(ValueError, match="background_linear"):
        ExportColorSpec(background_linear=(-1.0, 0.0, 0.0))


def test_export_rejects_nonfinite_rgba():
    rgba = np.zeros((2, 2, 4), dtype=np.float64)
    rgba[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        linear_rgba_to_srgb_rgb(rgba)
