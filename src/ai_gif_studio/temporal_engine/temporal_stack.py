"""Reusable deterministic stacks for explicit-time RenderBuffer effects."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np

from .render_buffer import RenderBuffer

TemporalEffect = Callable[[tuple[RenderBuffer, ...], float], RenderBuffer]


@dataclass(frozen=True, slots=True)
class TemporalEffectStack:
    """Immutable ordered stack of explicit-time unary RenderBuffer effects."""

    effects: tuple[TemporalEffect, ...] = ()

    def __post_init__(self) -> None:
        effects = tuple(self.effects)
        if len(effects) > 32:
            raise ValueError("a TemporalEffectStack may contain at most 32 effects")
        if any(not callable(effect) for effect in effects):
            raise TypeError("TemporalEffectStack effects must be callable")
        object.__setattr__(self, "effects", effects)

    def __call__(
        self,
        inputs: tuple[RenderBuffer, ...],
        time: float,
    ) -> RenderBuffer:
        source = _single_input(inputs)
        sample_time = _finite_time(time)
        current = source
        for effect in self.effects:
            result = effect((current,), sample_time)
            if not isinstance(result, RenderBuffer):
                raise TypeError("TemporalEffectStack effects must return a RenderBuffer")
            current = result
        return current

    def append(self, effect: TemporalEffect) -> TemporalEffectStack:
        """Return a new stack with one temporal effect appended."""
        if not callable(effect):
            raise TypeError("TemporalEffectStack effect must be callable")
        if len(self.effects) >= 32:
            raise ValueError("a TemporalEffectStack may contain at most 32 effects")
        return TemporalEffectStack(self.effects + (effect,))

    def extend(self, effects: Iterable[TemporalEffect]) -> TemporalEffectStack:
        """Return a new stack with temporal effects appended in declaration order."""
        additions = tuple(effects)
        if any(not callable(effect) for effect in additions):
            raise TypeError("TemporalEffectStack effects must be callable")
        if len(self.effects) + len(additions) > 32:
            raise ValueError("a TemporalEffectStack may contain at most 32 effects")
        return TemporalEffectStack(self.effects + additions)


def _single_input(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
    if len(inputs) != 1:
        raise ValueError("TemporalEffectStack requires exactly one RenderBuffer input")
    source = inputs[0]
    if not isinstance(source, RenderBuffer):
        raise TypeError("TemporalEffectStack input must be a RenderBuffer")
    return source


def _finite_time(time: float) -> float:
    if not np.isfinite(time):
        raise ValueError("TemporalEffectStack sample time must be finite")
    return float(time)
