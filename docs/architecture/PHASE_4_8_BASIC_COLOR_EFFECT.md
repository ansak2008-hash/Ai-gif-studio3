# Phase 4.8 — Generic Unary Color Effect Contract

## Objective

Prove the Phase 4.7 mask-aware graph abstraction with a reusable, deterministic unary color effect.

The first effect is deliberately small: exposure adjustment in canonical linear RGB. It is an architectural probe, not a complete color-management system.

## Contract

ExposureEffect(exposure_stops) is a callable RenderNode process:

- accepts exactly one RenderBuffer;
- preserves spatial dimensions;
- preserves alpha unchanged;
- multiplies linear RGB by 2 ** exposure_stops;
- rejects non-finite exposure;
- rejects wrong input count/type;
- returns an independent canonical RenderBuffer;
- never mutates the source.

The effect is mask-agnostic. Selective application is supplied by the existing Phase 4.7 RenderNode(mask=...) contract.

## Why

This separation proves the intended architecture:

Effect math -> RenderNode -> optional RenderMask

rather than:

MaskedExposureEffect, MaskedBlurEffect, MaskedGlowEffect, etc.

That prevents combinatorial growth as effects are added.

## Non-goals

No color-space conversion, tone mapping, clipping policy beyond the canonical RenderBuffer contract, GPU execution, plugin API, or effect registry.
