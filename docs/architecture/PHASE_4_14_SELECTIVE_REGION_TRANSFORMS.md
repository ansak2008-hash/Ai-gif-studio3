# Phase 4.14 — Selective Region Transforms

## Objective

Provide one reusable, typed boundary for applying an existing unary RenderBuffer transform
to a selected region without introducing a second mask representation or a parallel effect system.

## Contract

SelectiveRegionEffect(transform, mask):

- accepts one unary RenderBuffer transform callable;
- requires the canonical RenderMask;
- validates input type and mask dimensions before executing the transform;
- executes the transform against an owned copy of the source;
- requires a new RenderBuffer with unchanged dimensions;
- blends source and transformed RGBA values using mask coverage;
- returns independent storage and never mutates the caller's source;
- supports zero, full, and intermediate mask coverage deterministically.

## Architectural integration

The effect is intentionally small and reuses existing primitives:

- RenderBuffer remains the canonical pixel container;
- RenderMask remains the only mask representation;
- existing color, tone-curve, blend, and future unary transforms remain responsible for their own math;
- RenderGraph delegates its existing masked-node composition to this canonical effect.

This turns the existing graph mask behavior into a reusable capability rather than duplicating the same
mask-composition algorithm in another feature.

## Boundary guarantees

- no implicit clipping or color-space conversion;
- no mutation or aliasing of caller-owned input;
- no dimension-changing transform;
- no multi-input/fan-in selective transform;
- no layer registry, plugin system, GPU path, serialization, or runtime dependency.

## Non-goals

Transforms themselves are not added in this phase. The phase adds the reusable selective-region
orchestration boundary so existing deterministic unary transforms can be applied selectively.
