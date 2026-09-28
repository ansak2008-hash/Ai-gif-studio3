# Phase 4.6 RenderMask Contract

## Purpose

Establish a canonical, deterministic mask value for selective rendering and effects without changing RenderBuffer semantics or adding effect-specific logic.

## Contract

`RenderMask` represents one scalar coverage/control field:

- storage is canonical `float32`;
- shape is exactly `HxW`;
- dimensions are positive;
- every value is finite;
- values are constrained to the closed interval `[0, 1]`;
- constructor/factories own input storage;
- public `data` is read-only;
- `copy()` returns independent storage;
- `allocate(width, height, value=0)` creates a canonical mask;
- `from_array()` validates and canonicalizes floating-point input;
- inputs are never mutated;
- no implicit premultiplication, color conversion, clamping, or resampling occurs;
- `RenderMask` is intentionally separate from `RenderBuffer` because a mask is scalar control data, not RGBA render data.

## Design boundary

Phase 4.6 does not introduce effect nodes, GPU execution, graph mutation, color management, or mask resampling. Later phases may consume `RenderMask` through explicit node contracts.

The mask boundary is deliberately strict so invalid coverage cannot silently enter selective effects.

## Verification

Follow:

Contract → Tests → Implementation → CI → Adversarial Review → Merge.

Tests must cover valid construction, ownership/read-only behavior, invalid shape/type/range/non-finite values, allocation, copy independence, and determinism.
