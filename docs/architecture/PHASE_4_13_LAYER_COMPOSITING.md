# Phase 4.13 — Deterministic Layer Compositing

## Objective

Add a small typed orchestration boundary for ordered layer composition on top of the existing
RenderBuffer, RenderMask, BlendMode, and BlendModeEffect contracts.

## Contract

BlendLayer contains:
- one source RenderBuffer;
- one typed BlendMode;
- an optional canonical RenderMask.

composite_blend_layers(base, layers):
- accepts one base RenderBuffer and an ordered iterable of BlendLayer values;
- evaluates layers back-to-front in declaration order;
- reuses BlendModeEffect for every layer;
- returns an independent RenderBuffer;
- never mutates or aliases caller-owned buffers;
- accepts empty iterables and returns an independent copy of the base;
- validates layer, source, mode, mask, buffer-shape, and mask-shape boundaries.

## Architectural boundary

This phase is orchestration, not a new rendering kernel. Blend formulas remain owned by
BlendModeEffect; mask ownership remains in RenderMask; canonical pixel ownership remains in RenderBuffer.

No layer registry, plugin system, GPU path, color-space conversion, implicit clipping,
serialization, UI layer model, or new runtime dependency is introduced.

## Non-goals

No transforms, motion, opacity abstraction, layer graph, serialization format, or editor state.