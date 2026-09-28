# Phase 4.16 — Canonical Affine and Perspective Transforms

## Objective

Add reusable affine and four-point perspective transforms for the canonical RenderBuffer path without duplicating legacy uint8 frame helpers.

## Contract

AffineTransformEffect(spec) and PerspectiveTransformEffect(spec) are unary deterministic RenderBuffer transforms.

### Affine mode

AffineTransformSpec contains:
- positive target width and height;
- a finite 2x3 float transform matrix;
- an interpolation policy fixed to linear sampling for this phase;
- transparent-black output for samples outside the source.

The matrix uses the standard OpenCV source-to-destination affine convention.

A degenerate affine linear component is rejected when its rank is less than two.

### Perspective mode

PerspectiveTransformSpec contains:
- positive target width and height;
- four finite source points;
- four finite destination points;
- transparent-black output for samples outside the source.

The four-point mapping must define a non-degenerate projective transform.

### Boundary guarantees

- input and output remain canonical linear-light RGBA RenderBuffer values;
- output dimensions exactly equal the requested target;
- no implicit color conversion, clipping, or alpha reinterpretation;
- source input is never mutated or aliased;
- behavior is deterministic for identical input/specification;
- invalid dimensions, non-finite matrices/points, and degenerate transforms are rejected;
- no new mask, registry, capability graph, GPU path, or runtime dependency.

## Architectural integration

The phase introduces canonical geometry-transform primitives for the temporal-engine path. Existing legacy uint8 affine and perspective helpers remain compatibility boundaries and are not rewritten in this phase.

FramingEffect remains responsible for crop/fit/fill geometry policies; these effects are explicit geometric warps and therefore remain separate primitives.

## Non-goals

- no arbitrary interpolation abstraction;
- no color-management changes;
- no legacy pipeline migration;
- no UI or project-model integration;
- no transform-keyframe or motion system;
- no GPU implementation.
