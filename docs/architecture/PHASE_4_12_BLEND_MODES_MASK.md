# Phase 4.12 — Deterministic Blend Modes and Masks

## Objective

Add a reusable binary blend primitive over canonical linear RGBA plus an optional immutable RenderMask, without changing RenderBuffer or compositor contracts.

## Contract

BlendModeEffect accepts exactly two RenderBuffer inputs in `(destination, source)` order and an optional RenderMask.

Supported blend modes:
- normal
- multiply
- screen
- overlay

The RGB blend function operates on unassociated source/destination RGB values. The blended source RGB is then composited over the destination using source alpha.

If a mask is supplied:
- its dimensions must match both buffers;
- mask coverage multiplies source alpha only;
- mask data is never mutated;
- mask values remain canonical `[0, 1]`.

The effect:
- preserves destination dimensions;
- preserves source/destination inputs;
- returns an independent RenderBuffer;
- preserves destination alpha when source alpha is zero;
- uses explicit deterministic formulas;
- performs no color-space conversion, clamping, normalization, or implicit premultiplication;
- delegates final finite/canonical validation to RenderBuffer.

## Numerical boundary

All blend arithmetic is performed in float64 working space before the result crosses the existing RenderBuffer float32 validation boundary. Non-finite results are rejected by RenderBuffer rather than silently repaired.

## Architectural rationale

Blend math belongs in one typed reusable primitive. RenderMask already owns canonical mask validation, so this phase composes existing ownership boundaries instead of introducing a second mask representation.

## Non-goals

No layer graph, blend registry, GPU path, color-space conversion, automatic clipping, serialization, UI preset system, or new runtime dependency.
