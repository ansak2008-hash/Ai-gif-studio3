from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.temporal_effects import TemporalFadeEffect

pytestmark = pytest.mark.unit


def _source() -> RenderBuffer:
    data = np.zeros((4, 5, 4), dtype=np.float32)
    data[..., :3] = np.asarray([0.2, 0.4, 0.8], dtype=np.float32)
    data[..., 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def test_temporal_fade_linearly_samples_alpha() -> None:
    source = _source()
    result = TemporalFadeEffect(0.0, 1.0, 1.0, 0.0)((source,), 0.25)

    np.testing.assert_allclose(result.data[..., :3], source.data[..., :3])
    np.testing.assert_allclose(result.data[..., 3], 0.75)


def test_temporal_fade_clamps_endpoints_and_is_reusable() -> None:
    effect = TemporalFadeEffect(0.0, 1.0, 1.0, 0.0)
    source = _source()
    before = source.data.copy()

    early = effect((source,), -1.0)
    late = effect((source,), 2.0)
    again = effect((source,), 0.5)

    assert np.all(early.data[..., 3] == 1.0)
    assert np.all(late.data[..., 3] == 0.0)
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(again.data, effect((source,), 0.5).data)


def test_temporal_fade_rejects_invalid_contract() -> None:
    with pytest.raises(ValueError, match="greater than"):
        TemporalFadeEffect(1.0, 1.0)
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        TemporalFadeEffect(0.0, 1.0, 1.1)
    with pytest.raises(ValueError, match="finite"):
        TemporalFadeEffect(0.0, 1.0)((_source(),), float("nan"))
