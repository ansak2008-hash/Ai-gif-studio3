# Phase 4.17 — Reusable Effect Stacks

## Objective

Add one immutable reusable composition primitive for unary canonical RenderBuffer effects.

## Contract

EffectStack is an ordered tuple of callable unary effects. Each effect receives exactly one RenderBuffer and must return a RenderBuffer.

- effects execute strictly in declaration order;
- the same stack can be reused for multiple inputs;
- stack configuration is immutable;
- an empty stack is an identity operation;
- a stack contains at most 32 effects;
- invalid inputs, non-callable effects, and non-RenderBuffer effect results are rejected;
- outputs remain canonical linear-light RGBA RenderBuffer values;
- the stack never mutates its input;
- behavior is deterministic when its component effects are deterministic.

append() and extend() return new stacks rather than mutating an existing stack.

## Architectural integration

The stack reuses the existing unary effect contract and RenderBuffer boundary. It does not introduce an effect registry, plugin system, dynamic dispatch table, graph abstraction, serialization format, or new runtime dependency.

Existing legacy uint8 TransformSpec chains remain unchanged. EffectStack is the canonical composition primitive for the newer RenderBuffer temporal-engine effects.

## Non-goals

- no keyframe or timeline parameters;
- no per-layer motion;
- no effect metadata or UI model;
- no persistence or preset serialization;
- no automatic dependency/capability inference;
- no parallel execution or GPU path.
