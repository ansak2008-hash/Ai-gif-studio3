# Phase 4.9 — Reusable Color Effect Family

## Objective

Expand the Phase 4.8 unary color-effect architecture with two deterministic, reusable linear-RGB effects without introducing mask-specific variants or an effect registry.

## Shared Contract

Every effect in this phase:

- is a callable compatible with the RenderNode process contract;
- accepts exactly one RenderBuffer;
- preserves spatial dimensions;
- preserves alpha unchanged;
- returns an independent canonical RenderBuffer;
- never mutates its source;
- rejects invalid effect parameters before processing;
- remains mask-agnostic;
- is deterministic for identical inputs and parameters.

Selective application remains the responsibility of RenderNode and RenderMask.

## GammaEffect

GammaEffect(gamma):

- requires finite gamma strictly greater than zero;
- transforms linear RGB as RGB' = RGB ** gamma;
- preserves alpha;
- does not clamp or convert color spaces;
- relies on RenderBuffer for canonical finite/nonnegative validation.

## RGBGainEffect

RGBGainEffect(red, green, blue):

- requires three finite, nonnegative gains;
- multiplies each linear-RGB channel by its corresponding gain;
- preserves alpha;
- does not clamp or convert color spaces;
- relies on RenderBuffer for canonical finite/nonnegative validation.

## Architectural Rationale

The effects contain only effect math. RenderNode owns graph execution and optional RenderMask owns selective interpolation:

Effect math -> RenderNode -> optional RenderMask

This avoids creating combinations such as MaskedGammaEffect or MaskedRGBGainEffect.

A formal effect registry or broad effect protocol is intentionally deferred until multiple effect families require shared lifecycle, metadata, serialization, or discovery semantics.

## Non-goals

No tone mapping, color-space conversion, GPU execution, plugin API, effect registry, blur, convolution, resampling, or automatic clipping policy.
