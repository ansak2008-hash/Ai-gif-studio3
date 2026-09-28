# Phase 4.10 — Color Matrix Effect

## Objective

Introduce one general deterministic affine RGB transform primitive for reusable color operations without duplicating effect-specific channel math.

## Contract

ColorMatrixEffect(matrix) requires a finite floating-point 3x4 matrix.

For each pixel, with linear RGB vector c = [R, G, B]:

`c' = M[:3, :3] @ c + M[:3, 3]`

Alpha is preserved unchanged.

The effect:

- accepts exactly one RenderBuffer;
- operates only on canonical linear RGB;
- preserves dimensions;
- returns an independent RenderBuffer;
- never mutates its source;
- rejects non-floating, wrong-shape, or non-finite matrices;
- does not clamp, resample, or perform color-space conversion;
- relies on RenderBuffer validation for the output canonical contract;
- remains mask-agnostic.

## Matrix Ownership

The constructor copies the matrix into immutable owned storage so later caller mutation cannot alter effect behavior.

## Architectural Rationale

A matrix primitive covers a broad class of linear/affine color transforms while keeping the effect layer small. Higher-level effects can later construct matrices without changing RenderGraph or RenderMask.

This is intentionally not a general expression evaluator or plugin system.

## Non-goals

No tone mapping, gamma/power transforms, GPU execution, color-space conversion, resampling, effect registry, serialization format, or automatic clipping.
