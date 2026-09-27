# Phase 3 — PBR / GGX Architecture Gate

Status: **architecture gate / design baseline**  
Baseline commit: `126506e6505ac54d57063684eefd1d70f752f7a6`  
Branch: `codex/phase-3-pbr-architecture`

## Purpose

Phase 3 introduces a physically based material/shading path without reopening the
Phase 2 perspective/depth foundation.

The implementation target is a deterministic, vectorized Cook-Torrance BRDF
using GGX microfacet distribution, Smith masking-shadowing, and
Fresnel-Schlick.

## Scope

### In scope

1. New isolated module: `src/ai_gif_studio/temporal_engine/material_pbr.py`.
2. Material parameters:
   - base color in linear RGB
   - metallic in [0, 1]
   - roughness in a validated non-zero range
   - optional dielectric/specular control only where required by the final contract
3. GGX normal distribution function (NDF).
4. Smith masking-shadowing geometry term.
5. Fresnel-Schlick approximation.
6. Cook-Torrance specular BRDF.
7. Explicit diffuse/specular energy handling for metallic materials.
8. Deterministic lighting evaluation over canonical Phase 2 normals.
9. Unit tests for mathematical invariants before renderer integration.
10. Integration tests only after the pure PBR contract is stable.

### Explicitly out of scope for the first P3 increment

- Rewriting `camera.py`.
- Changing `depth_field.py`, `bevel.py`, or affine math.
- Extending the legacy `material.py`.
- Replacing the manuscript renderer.
- Environment/IBL.
- Image-based lighting.
- Shadows.
- Tone mapping redesign.
- GPU-specific implementation.
- Unrelated lint/refactoring/database work.

## Existing Phase 2 contracts

### Canonical normals

`DepthField.from_alpha()` is the canonical source of surface normals for
the new path. Its normal tensor is `(H, W, 3)), finite, deterministic, and
unit-normalized. Transparent pixels use the canonical normal
`[0, 0, 1]`.

Phase 3 must consume this contract rather than recomputing normals from alpha.

### Color space

The PBR path operates on **linear RGB** values. sRGB encoding remains an
output-stage concern.

### Camera

The Phase 2 camera projection remains unchanged. Phase 3 consumes camera-derived
view vectors/positions; it does not alter projection mathematics.

## Proposed pure API

The first implementation should expose small pure functions rather than a
renderer-wide object graph:

- `fresnel_schlick(cos_theta, f0)`
- `ggx_distribution(ndoth, roughness)`
- `smith_geometry(ndotv, ndotl, roughness)`
- `cook_torrance_specular(ndotv, ndotl, ndoth, vdoth, roughness, f0)`
- `shade_pbr(base_color, metallic, roughness, normal, view_dir, light_dir, light_color, ...)`

Exact signatures may be refined during implementation, but the mathematical
responsibilities must remain separated so each component can be tested
independently.

## Mathematical contract

For normalized vectors:

- (N) = surface normal
- (V) = view direction
- (L) = light direction
- (H = normalize(V + L))

Required dot products are clamped to the physically meaningful domain
([0,1]).

Cook-Torrance specular:

[
f_s =
\frac{D(N,H) F(V,H) G(N,V,L)}
     {4 (N,V)(N,L)}
]

GGX, Smith, and Fresnel implementations must remain finite for all valid input
ranges and must not emit NaN/Inf at grazing angles.

The implementation must avoid divisions by zero by explicit bounded denominators,
not by masking an already-invalid result after the fact.

## Validation contract

Before any renderer integration:

### Unit tests

- Fresnel at normal incidence.
- Fresnel at grazing incidence.
- Fresnel monotonicity over valid cosine range.
- GGX non-negativity and finiteness.
- Roughness boundary behavior.
- Smith term boundedness.
- Cook-Torrance non-negativity and finiteness.
- Normalization/invariance checks for normalized directions.
- Deterministic repeated evaluation.
- Metallic/dielectric energy behavior according to the selected material model.

Floating-point comparisons use `assert_allclose`; exact deterministic output uses
`assert_array_equal` only where exact equality is the intended contract.

### Integration tests

Only after pure functions pass:

- canonical DepthField normals → PBR shading
- linear RGB input/output contract
- deterministic repeated frame shading
- transparent-pixel behavior
- compatibility with the existing temporal engine

## Change-control rules

1. Phase 2 files are protected from opportunistic refactoring.
2. `material.py` remains legacy and is not extended.
3. Every mathematical change must have a corresponding test.
4. No tolerance weakening to make a test pass.
5. No `noqa` suppression for PBR correctness or lint.
6. No test deletion or scope reduction.
7. No bulk formatter/linter rewrite.
8. External review reports are treated as hypotheses and verified against the
   repository and CI before changes are applied.
9. Each P3 increment should remain small enough to diagnose from one commit.
10. CI must run after each meaningful increment.

## Gate sequence

```
Architecture baseline
    ↓
Pure mathematical primitives
    ↓
Mathematical unit tests
    ↓
PBR shading function
    ↓
PBR unit + determinism tests
    ↓
DepthField/camera integration
    ↓
Integration tests
    ↓
CI + forensic audit
    ↓
Renderer integration
```

This document is an architecture gate, not an implementation claim. No PBR/GGX
implementation is considered complete until the corresponding code and tests
exist and the CI evidence is green.
