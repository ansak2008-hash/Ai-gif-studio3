# Phase 4.23 — Deterministic Temporal Layer Composition

## Objective

Add the smallest end-to-end temporal scene composition primitive: sample an ordered sequence of MotionLayer values at one explicit time and composite the resulting BlendLayer values over a canonical base.

## Contract

- Canonical call: composite_motion_layers(base, layers, time).
- base must be a RenderBuffer.
- layers is an ordered iterable containing only MotionLayer values.
- sample time must be finite.
- Each MotionLayer is sampled exactly once at the same explicit time.
- Declaration order is preserved when compositing.
- The existing composite_blend_layers compositor performs the actual layer composition.
- An empty layer sequence returns an independent copy of base.
- Inputs and MotionLayer sources are never mutated.
- Repeated calls with identical inputs and time are deterministic.

## Architectural integration

This is orchestration, not a second renderer. It binds the existing MotionLayer sampler to the existing BlendLayer compositor.

No new timeline, clock, scheduler, layer descriptor, blend implementation, registry, graph, serialization model, GPU path, or runtime dependency is introduced.

The function intentionally accepts MotionLayer rather than introducing a parallel temporal-layer type.

## Non-goals

- No implicit current-time state.
- No frame scheduling or timeline ownership.
- No project/revision graph.
- No transition registry.
- No persistence or UI model.
- No AI/provider integration.
- No new runtime dependency.

## Verification

The phase must pass contract tests, Ruff, CI, CodeQL, adversarial architectural review, and final diff/PR review before merge.
