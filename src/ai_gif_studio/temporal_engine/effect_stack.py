"""Reusable deterministic effect stacks for canonical RenderBuffer values."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .render_buffer import RenderBuffer

RenderEffect = Callable[[tuple[RenderBuffer, ...]], RenderBuffer]


@dataclass(frozen=True, slots=True)
class EffectStack:
    """Immutable ordered stack of unary RenderBuffer effects."""

    effects: tuple[RenderEffect, ...] = ()

    def __post_init__(self) -> None:
        effects = tuple(self.effects)
        if len(effects) > 32:
            raise ValueError("an EffectStack may contain at most 32 effects")
        if any(not callable(effect) for effect in effects):
            raise TypeError("EffectStack effects must be callable")
        object.__setattr__(self, "effects", effects)

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        source = _single_input(inputs)
        current = source
        for effect in self.effects:
            result = effect((current,))
            if not isinstance(result, RenderBuffer):
                raise TypeError("EffectStack effects must return a RenderBuffer")
            current = result
        return current

    def append(self, effect: RenderEffect) -> EffectStack:
        """Return a new stack with one effect appended."""
        if not callable(effect):
            raise TypeError("EffectStack effect must be callable")
        if len(self.effects) >= 32:
            raise ValueError("an EffectStack may contain at most 32 effects")
        return EffectStack(self.effects + (effect,))

    def extend(self, effects: Iterable[RenderEffect]) -> EffectStack:
        """Return a new stack with effects appended in declaration order."""
        additions = tuple(effects)
        if any(not callable(effect) for effect in additions):
            raise TypeError("EffectStack effects must be callable")
        if len(self.effects) + len(additions) > 32:
            raise ValueError("an EffectStack may contain at most 32 effects")
        return EffectStack(self.effects + additions)


def _single_input(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
    if len(inputs) != 1:
        raise ValueError("EffectStack requires exactly one RenderBuffer input")
    source = inputs[0]
    if not isinstance(source, RenderBuffer):
        raise TypeError("EffectStack input must be a RenderBuffer")
    return source
