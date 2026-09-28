"""Contract tests for the explicit-time temporal effect stack."""
from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.effect_stack import EffectStack
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.temporal_effects import TemporalFadeEffect
from ai_gif_studio.temporal_engine.temporal_stack import TemporalEffectStack

pytestmark = pytest.mark.unit


def _buffer() -> RenderBuffer:
    data = np.zeros((2, 2, 4), dtype=np.float32)
    data[..., :3] = 0.4
    data[..., 3] = 1.0
    return RenderBuffer.from_linear_rgba(data)


def test_temporal_stack_applies_effects_in_declaration_order() -> None:
    source = _buffer()
    calls: list[tuple[str, float]] = []

    def first(inputs: tuple[RenderBuffer, ...], time: float) -> RenderBuffer:
        calls.append(("first", time))
        return inputs[0]

    def second(inputs: tuple[RenderBuffer, ...], time: float) -> RenderBuffer:
        calls.append(("second", time))
        return inputs[0]

    result = TemporalEffectStack((first, second))((source,), 0.25)

    assert result is source
    assert calls == [("first", 0.25), ("second", 0.25)]


def test_temporal_stack_composes_temporal_fade_effects() -> None:
    source = _buffer()
    fade_out = TemporalFadeEffect(0.0, 1.0, 1.0, 0.5)
    fade_in = TemporalFadeEffect(0.0, 1.0, 1.0, 0.5)

    result = TemporalEffectStack((fade_out, fade_in))((source,), 0.5)

    np.testing.assert_allclose(result.data[..., 3], 0.5625)
    np.testing.assert_allclose(source.data[..., 3], 1.0)


def test_empty_temporal_stack_is_identity() -> None:
    source = _buffer()

    assert TemporalEffectStack()((source,), 10.0) is source


def test_temporal_stack_is_reusable_and_does_not_mutate_source() -> None:
    source = _buffer()
    stack = TemporalEffectStack((TemporalFadeEffect(0.0, 1.0),))

    first = stack((source,), 0.25)
    second = stack((source,), 0.25)

    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(source.data[..., 3], 1.0)


def test_temporal_stack_normalizes_mutable_effect_collection() -> None:
    effects = [TemporalFadeEffect(0.0, 1.0)]
    stack = TemporalEffectStack(effects)

    effects.clear()

    assert isinstance(stack.effects, tuple)
    assert len(stack.effects) == 1


def test_append_and_extend_return_new_stacks() -> None:
    effect = TemporalFadeEffect(0.0, 1.0)
    base = TemporalEffectStack()
    appended = base.append(effect)
    extended = base.extend([effect, effect])

    assert base.effects == ()
    assert appended.effects == (effect,)
    assert extended.effects == (effect, effect)


def test_temporal_stack_rejects_invalid_inputs_time_effects_and_outputs() -> None:
    stack = TemporalEffectStack((TemporalFadeEffect(0.0, 1.0),))

    with pytest.raises(ValueError, match="exactly one"):
        stack((), 0.5)
    with pytest.raises(TypeError, match="RenderBuffer"):
        stack((object(),), 0.5)
    with pytest.raises(ValueError, match="finite"):
        stack((_buffer(),), float("nan"))

    with pytest.raises(TypeError, match="callable"):
        TemporalEffectStack((object(),))


def test_temporal_stack_rejects_invalid_component_output() -> None:
    def invalid(inputs: tuple[RenderBuffer, ...], time: float) -> object:
        return object()

    with pytest.raises(TypeError, match="RenderBuffer"):
        TemporalEffectStack((invalid,))((_buffer(),), 0.5)


def test_temporal_stack_enforces_size_limit() -> None:
    effect = TemporalFadeEffect(0.0, 1.0)
    with pytest.raises(ValueError, match="32"):
        TemporalEffectStack((effect,) * 33)

    full = TemporalEffectStack((effect,) * 32)
    with pytest.raises(ValueError, match="32"):
        full.append(effect)
    with pytest.raises(ValueError, match="32"):
        full.extend([effect])


def test_temporal_stack_does_not_replace_the_non_temporal_effect_contract() -> None:
    effect = lambda inputs: inputs[0]
    assert EffectStack((effect,))((_buffer(),)).shape == (2, 2, 4)
