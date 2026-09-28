# Phase 4.21 — Temporal Effect Stack Contract

## Objective

Provide one minimal immutable composition boundary for explicit-time effects so multiple time-sampled effects can be applied in deterministic declaration order without creating a second timeline, clock, scheduler, or renderer.

## Public contract

- `TemporalEffect` is a callable with signature `(inputs: tuple[RenderBuffer, ...], time: float) -> RenderBuffer`.
- `TemporalEffectStack(effects=...)` stores an immutable ordered tuple of temporal effects.
- `stack((source,), time)` applies each effect as `effect((current,), time)`.
- Empty stack is the identity.
- `append()` and `extend()` return new stacks and never mutate an existing stack.
- Effect collections are normalized to tuples at construction.
- Maximum stack length is 32.
- Inputs must contain exactly one `RenderBuffer`.
- Sample time must be finite.
- Every component effect must be callable and must return a `RenderBuffer`.

## Invariants

- Input `RenderBuffer` is never mutated by the stack itself.
- Component effects execute strictly in declaration order.
- The stack introduces no hidden current-time state.
- Given deterministic component effects and identical inputs/time, output is deterministic.
- No aliasing or mutable configuration is introduced by the stack container.

## Compatibility and reuse

- Reuses canonical `RenderBuffer`.
- Preserves the existing unary `EffectStack` contract for non-temporal effects.
- `TemporalFadeEffect` remains an explicit-time effect and can be composed by this stack without changing its signature.
- No second timeline, clock, scheduler, renderer, layer model, registry, dynamic dispatch table, serialization format, GPU path, or runtime dependency is introduced.

## Explicit non-goals

- No implicit current time.
- No keyframe storage or interpolation.
- No timeline ownership or frame scheduling.
- No automatic conversion between temporal and non-temporal effect protocols.
- No parallel execution.
