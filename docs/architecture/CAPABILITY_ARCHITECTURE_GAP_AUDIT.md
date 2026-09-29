# Capability & Architecture Gap Audit

## Purpose

This document records the repository-grounded capability audit before adding the next professional editing algorithms.

The goal is to extend the editor without duplicating existing foundations or creating architectural lock-in.

## Verified foundations already present

The repository already contains:

- canonical owned/read-only RenderBuffer;
- canonical owned/read-only RenderMask;
- layer state and bounded LayerStack;
- blend modes and compositor contracts;
- ordered EffectStack and temporal EffectStack;
- affine transforms, perspective/geometry primitives, and transform-to-render binding;
- MotionCurve and immutable AffineTransformTrack keyframe sampling;
- per-layer MotionLayer;
- ToneCurveEffect and ColorMatrixEffect;
- linear RGB / sRGB conversion and explicit export color handling;
- ResourceManager admission/reservation/release infrastructure;
- immutable ProjectState and revision/persistence boundaries.

Do not rebuild these as parallel abstractions.

## P0/P1 gaps

### 1. First-class editable mask state

RenderMask exists as a render-time scalar field, but LayerState does not currently carry a persistent mask reference or mask-editing state.

This prevents professional non-destructive workflows such as:

Layer -> content -> opacity -> blend -> mask -> mask edits -> revision history.

Required eventual contract:

- mask is an owned immutable project-domain value or stable asset reference;
- mask can be serialized/deserialized deterministically;
- mask edits are revision/command operations;
- render binding consumes the canonical RenderMask;
- mask operations include at minimum create, invert, feather/blur, levels/threshold, and composition;
- no flattened pixel replacement is required.

Do not implement a generic mask registry.

### 2. Explicit color-domain/encoding contract

The renderer is correctly centered on linear RGBA, but color handling is not yet represented by one explicit domain/encoding contract.

In particular, `linearize_srgb()` contains a heuristic that divides floating values above 1 by 255. That behavior is unsafe as a general HDR color-domain rule because values above 1 may be valid linear HDR values.

Before 3D LUT, broad adjustment layers, or HDR workflows expand, define:

- color domain/encoding;
- transfer function;
- primaries/profile identity where needed;
- alpha semantics;
- valid numeric domain;
- whether an operation is scene-referred or display-referred;
- explicit conversion boundaries.

Do not introduce automatic LogC/S-Log3 or other camera encodings without a concrete contract.

## P1 capability gaps after foundations

### Adjustment-layer semantics

The effect primitives already cover important mathematics, but the project does not yet have a persistent adjustment-layer domain model.

The future abstraction should describe editable intent and parameters, not duplicate effect math.

### Professional typography

There is no verified editable TextLayer domain model yet.

Arabic/English typography requires explicit contracts for font identity, shaping, size, weight, tracking, leading, alignment, fill/stroke, opacity, transform, and deterministic fallback/failure behavior.

### Vector design primitives

There is no verified first-class vector path/shape domain model.

Vector geometry should remain vector until the render boundary.

### Non-destructive source preservation

There is no verified SmartObject-like source-preservation domain model.

Do not build one until its relationship with ProjectState and the Revision Graph is explicit.

### Layer styles

There is no verified persistent LayerStyle model for stroke, shadow, glow, overlays, bevel/emboss, etc.

These should compose with the existing effect/compositor contracts rather than create a second renderer.

## Motion architecture observation

The project already has MotionCurve and AffineTransformTrack, which solve different sampling problems.

Do not merge them prematurely.

Before broad property animation is added, define a property-track contract that can represent transform, opacity, and effect parameters without creating a second timeline or implicit clock.

## Correct next implementation sequence

1. Finish and adversarially close Phase 5.12 rotation.
2. Land the repository engineering operating strategy.
3. Harden first-class mask state and mask editing semantics.
4. Harden explicit color-domain/encoding semantics and remove ambiguous HDR heuristics.
5. Build the 3D LUT contract on top of that explicit color boundary.
6. Build frequency separation with explicit alpha/color reconstruction semantics.
7. Continue with warp/selection/content-aware families after resource and determinism contracts are proven.

## Anti-regression rule

Do not implement a visually impressive algorithm if its output semantics, color domain, ownership, serialization, resource bound, or revision behavior are still ambiguous.

## Permanent review question

Does the next capability compose with the existing engine without creating a second source of truth for state, time, color, ownership, or rendering?
