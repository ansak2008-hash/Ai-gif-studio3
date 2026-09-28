# Phase 4.15 — Canonical Framing Transforms

## Objective

Add reusable crop/fit/fill policies for the canonical RenderBuffer path without duplicating the
legacy uint8 frame helpers.

## Contract

FramingEffect(spec) is a unary deterministic RenderBuffer transform.

FramingSpec contains:
- positive target width and height;
- one FramingMode: CROP, FIT, or FILL;
- normalized focus_x and focus_y in [0, 1].

### Modes

- CROP: select an exact target-sized window from the source without resampling. The target must
  not exceed the source dimensions. Focus controls the window position.
- FIT: scale the complete source uniformly so it fits inside the target, then place it centered
  on a transparent-black RenderBuffer. No source pixels are cropped.
- FILL: scale the source uniformly so the target is completely covered, then crop to the target.
  Focus controls the crop position.

### Boundary guarantees

- input and output remain canonical linear-light RGBA RenderBuffer values;
- output dimensions exactly equal the requested target;
- no implicit color conversion, clipping, or alpha reinterpretation;
- source input is never mutated or aliased;
- behavior is deterministic for identical input/specification;
- invalid dimensions, focus values, and impossible crop requests are rejected;
- no new mask, registry, capability graph, GPU path, or runtime dependency.

## Architectural integration

The phase introduces one generic framing primitive for the temporal-engine path. Existing legacy
uint8 crop helpers remain compatibility boundaries and are not rewritten in this phase.

The primitive is intentionally independent from SelectiveRegionEffect: framing changes geometry,
while selective-region transforms preserve geometry.

## Non-goals

- no affine/perspective transform implementation;
- no new interpolation abstraction;
- no color-management changes;
- no legacy pipeline migration;
- no UI or project-model integration.
