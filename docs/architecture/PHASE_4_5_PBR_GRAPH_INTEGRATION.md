# Phase 4.5 — PBR Graph Integration Contract

## Objective

Expose the existing Phase 3 deterministic direct-light PBR kernel as a RenderGraph node without duplicating BRDF mathematics.

## Contract

- The node consumes exactly one RenderBuffer input.
- Input alpha is preserved; material albedo comes from the existing immutable PBRMaterial contract.
- The node uses the existing `PBRMaterial` for roughness/metallic parameters and existing `DirectLight` values for ordered direct-light accumulation.
- Surface normal and view vectors are supplied by the node configuration and must match the RenderBuffer dimensions.
- PBR calculations remain float64. Conversion to canonical RenderBuffer float32 happens exactly once at the node output boundary.
- Output dimensions and alpha are identical to the input.
- Input storage is never mutated and output storage is independent.
- Direct-light order is explicit and deterministic.
- No IBL, Monte Carlo sampling, tone mapping, GPU code, or replacement PBR API is introduced.
- Invalid geometry, material, lights, non-finite output, or invalid RenderBuffer input must fail before returning a result.

## Energy coverage

The existing integrated direct-light energy test remains authoritative for endpoint metallic values. Phase 4.5 adds representative intermediate metallic/roughness cases to guard the graph adapter boundary; it does not introduce multi-scatter compensation.

## Precision boundary

`material_pbr.py` computes PBR math in float64. `RenderBuffer` is the canonical float32 linear RGBA storage. The adapter is the explicit precision boundary.
