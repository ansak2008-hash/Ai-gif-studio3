from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def test_security_media_contract_rejects_non_rgba_render_input() -> None:
    with pytest.raises(ValueError):
        RenderBuffer.from_linear_rgba(np.zeros((8, 8, 3), dtype=np.float32))


def test_security_media_contract_rejects_non_finite_input() -> None:
    rgba = np.zeros((8, 8, 4), dtype=np.float32)
    rgba[0, 0, 0] = np.inf
    with pytest.raises(ValueError):
        RenderBuffer.from_linear_rgba(rgba)


def test_security_media_contract_rejects_alpha_outside_bounds() -> None:
    rgba = np.zeros((8, 8, 4), dtype=np.float32)
    rgba[0, 0, 3] = 2.0
    with pytest.raises(ValueError):
        RenderBuffer.from_linear_rgba(rgba)


def test_security_media_contract_owns_input_storage() -> None:
    rgba = np.zeros((8, 8, 4), dtype=np.float32)
    buffer = RenderBuffer.from_linear_rgba(rgba)
    rgba[0, 0, 0] = 1.0
    assert buffer.data[0, 0, 0] == 0.0
