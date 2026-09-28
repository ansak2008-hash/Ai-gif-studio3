from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.effect_stack import EffectStack
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer

pytestmark = pytest.mark.unit


def _buffer(value: float = 1.0) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[[value, value * 2.0, value * 3.0, 1.0]]], dtype=np.float32)
    )


def _add(value: float):
    def effect(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = inputs[0]
        data = source.data.copy()
        data[..., :3] += value
        return RenderBuffer.from_linear_rgba(data)

    return effect


def test_stack_applies_effects_in_declaration_order() -> None:
    result = EffectStack((_add(1.0), _add(2.0)))(_buffer())
    np.testing.assert_array_equal(
        result.data,
        np.asarray([[[4.0, 5.0, 6.0, 1.0]]], dtype=np.float32),
    )


def test_stack_is_reusable_without_mutating_source() -> None:
    source = _buffer()
    before = source.data.copy()
    stack = EffectStack((_add(1.0), _add(2.0)))

    first = stack((source,))
    second = stack((source,))

    np.testing.assert_array_equal(first.data, second.data)
    np.testing.assert_array_equal(source.data, before)
    assert first is not source


def test_stack_normalizes_mutable_effect_collections() -> None:
    effects = [_add(1.0)]
    stack = EffectStack(effects)
    effects.append(_add(2.0))

    assert len(stack.effects) == 1
    assert isinstance(stack.effects, tuple)


def test_append_and_extend_return_immutable_new_stacks() -> None:
    first = EffectStack((_add(1.0),))
    second = first.append(_add(2.0))
    third = first.extend((_add(2.0), _add(3.0)))

    assert len(first.effects) == 1
    assert len(second.effects) == 2
    assert len(third.effects) == 3


def test_empty_stack_is_identity_with_owned_output() -> None:
    source = _buffer()
    result = EffectStack()((source,))

    assert result is source


def test_stack_rejects_invalid_inputs_effects_and_size() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        EffectStack()(())

    with pytest.raises(TypeError, match="RenderBuffer"):
        EffectStack()((object(),))  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="callable"):
        EffectStack((object(),))  # type: ignore[arg-type]

    stack = EffectStack(tuple(_add(1.0) for _ in range(32)))
    with pytest.raises(ValueError, match="32"):
        stack.append(_add(1.0))
    with pytest.raises(ValueError, match="32"):
        stack.extend((_add(1.0),))

    with pytest.raises(TypeError, match="callable"):
        stack.append(object())  # type: ignore[arg-type]


def test_stack_rejects_invalid_effect_output() -> None:
    def invalid(_inputs: tuple[RenderBuffer, ...]) -> object:
        return object()

    with pytest.raises(TypeError, match="RenderBuffer"):
        EffectStack((invalid,))(_buffer())
