# Phase 4.11 — Deterministic Tone Curve Effect

## Objective

Add a reusable LUT-style color grading primitive for canonical linear RGB without changing RenderGraph, RenderMask, or RenderBuffer contracts.

## Contract

ToneCurveEffect accepts one or three immutable ToneCurve values:

- one curve applies to R, G, and B;
- three curves apply independently to R, G, and B.

Each ToneCurve contains at least two finite (x, y) control points.

The curve contract:

- x coordinates are strictly increasing;
- x and y coordinates are finite floating-point values;
- interpolation is piecewise linear;
- values between control points are linearly interpolated;
- values outside the control-point domain use linear extrapolation from the nearest segment;
- no implicit clamping, normalization, or color-space conversion occurs;
- alpha is preserved unchanged;
- dimensions and canonical RenderBuffer validation remain owned by RenderBuffer;
- the effect accepts exactly one RenderBuffer;
- the source is never mutated;
- the result is an independent RenderBuffer;
- all curve arrays are copied into immutable owned storage.

## Numerical boundary

The implementation must not use a library interpolation primitive that silently clamps out-of-domain values. HDR/linear-light values outside the control-point x-domain remain representable through explicit endpoint extrapolation.

## Architectural rationale

A typed curve primitive covers reusable channel grading while keeping channel math out of individual effects. Higher-level presets can construct curves without adding a registry or plugin layer.

## Non-goals

No spline fitting, histogram analysis, automatic grading, tone mapping, color-space conversion, GPU execution, serialization format, effect registry, or automatic clipping.
