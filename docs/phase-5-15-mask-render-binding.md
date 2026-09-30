# Phase 5.15 Persistent Mask Render Binding

## Contract

`bind_layer_stack(stack, sources, *, masks=None)` is the explicit adapter from persistent layer state to compositor-ready layers.

- Existing unmasked callers remain compatible.
- A `LayerState.mask` is never silently ignored.
- A masked layer requires an explicit `masks` mapping.
- The mapping resolves `MaskState.source_asset_id` to an already materialized `RenderMask`.
- The resolved mask dimensions must equal the source `RenderBuffer` dimensions.
- `process_mask()` applies the persistent mask semantics before layer opacity.
- Layer opacity multiplies the processed mask after all persistent mask operations.
- Missing or incorrectly typed mask sources fail closed.
- Neither source buffers nor source masks are mutated.

## Compatibility

The `masks` parameter is keyword-only. Existing two-argument calls remain valid for layers without persistent masks.

A masked layer without the mapping is an error rather than silently falling back to an unmasked render. This prevents persistent editing state from disappearing at the render boundary.

## Ownership

The binding adapter does not take ownership of caller mappings or pixel storage. `process_mask()` returns a detached `RenderMask`, and opacity multiplication creates another detached canonical mask.

## Deferred

This phase does not add a global asset registry, plugin system, GPU path, or new mask representation. Asset lookup remains an explicit caller-provided mapping.