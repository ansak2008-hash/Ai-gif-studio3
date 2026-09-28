# Phase 4.22 — Deterministic Temporal Crossfade

## Objective

Add one minimal richer transition: an explicit-time crossfade between two canonical RenderBuffer inputs.

## Contract

- TemporalCrossfadeEffect(start_time, end_time) is immutable and stateless.
- Canonical call: effect((first, second), time).
- Exactly two RenderBuffer inputs are required.
- Inputs must have identical (height, width, 4) shapes.
- start_time and end_time must be finite, with end_time > start_time.
- Sample time must be finite.
- Progress is linear in the explicit time interval and clamped to [0, 1].
- At the endpoints, the result is an independent copy of the selected source.
- Between endpoints, RGB is interpolated through premultiplied RGB and alpha is linearly interpolated, then RGB is unpremultiplied.
- The returned value is a new canonical RenderBuffer.
- Inputs are never mutated or aliased.
- Repeated calls with identical inputs and time are deterministic.

## Architectural integration

The transition is a two-input temporal primitive. It deliberately does not become a member of TemporalEffectStack, whose contract is unary (inputs, time) -> RenderBuffer.

It reuses the canonical RenderBuffer representation and introduces no second timeline, clock, renderer, compositor, layer model, registry, scheduler, serialization system, GPU path, or runtime dependency.

TemporalCrossfadeEffect is a transition primitive, not a timeline or transition registry. More transition types should only be added when a concrete product requirement justifies them.

## Non-goals

- No easing registry or dynamic transition dispatch.
- No implicit current-time lookup.
- No automatic frame scheduling.
- No keyframe collection.
- No project/revision graph.
- No persistence or UI model.
- No provider/AI integration.
- No new runtime dependency.

## Verification

The phase must pass:

1. contract tests;
2. Ruff;
3. CI unit/integration/load gates where applicable;
4. CodeQL;
5. adversarial architectural review;
6. final diff and PR review before merge.
