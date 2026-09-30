# Phase 5.13 Mask Contract

## Scope

Phase 5.13 introduces the persistent domain contract for editable layer masks. It does not implement pixel-mask rendering or mask-processing algorithms.

## Ownership

- LayerState.mask is optional immutable persistent state.
- MaskState.source_asset_id identifies owned pixel storage.
- Pixel arrays are never embedded in ProjectState or MaskState.
- RenderMask remains the render-time float32 HxW primitive and owns detached read-only pixels.

## Canonical state

MaskState is content-bearing project state and therefore has deterministic canonical JSON. Its fields are:

- mask_id
- source_asset_id
- enabled
- inverted
- opacity in [0, 1]
- feather_radius in [0, 4096]
- blur_radius in [0, 4096]
- levels_low and levels_high in [0, 1], with levels_low < levels_high
- optional threshold in [0, 1]

Boolean values are rejected wherever numeric values are expected. Non-finite values are rejected.

## Backward compatibility

A layer without a mask retains the existing canonical JSON shape. Existing positional LayerState construction remains valid because mask is appended as the final optional field.

## Rendering semantics

The persistent state defines the semantic order; it does not prescribe a particular raster kernel.

1. Resolve source pixels to the canonical mask domain [0, 1].
2. If enabled is false, the effective mask is the identity field (1.0 everywhere); no other mask operation changes it.
3. Apply feather and blur as the spatial-filter stage. Both are deterministic edge-padded box filters over the canonical HxW field; `ceil(radius)` determines the half-width. A radius larger than the largest source dimension is clamped to `max(height, width) - 1`, preventing unbounded kernel/storage growth.
4. Apply levels remapping using levels_low and levels_high as the input interval, with output clamped to [0, 1].
5. If threshold is present, map values below threshold to 0.0 and values at or above it to 1.0.
6. If inverted is true, replace m with 1.0 - m.
7. Apply mask opacity as m * opacity.

This ordering is part of the contract so future render implementations cannot silently change editing semantics.

## Rendering boundary

Persistent mask state does not expose mutable pixel storage. A later render stage resolves source_asset_id and materializes a RenderMask. Mask operations must be deterministic and must not mutate the source asset or the render-time mask. The source asset is never modified in place.

## Phase 5.14 processing boundary

The render boundary is `process_mask(RenderMask, MaskState) -> RenderMask`. It validates both contracts, never mutates the source, performs all intermediate arithmetic in float64, and returns an owned read-only float32 `RenderMask`.

The disabled state is a deliberate identity override: it returns an all-ones mask and skips every other operation. This prevents disabled masks from accidentally altering rendering through stale adjustment fields.

The spatial stage uses two ordered edge-padded box-filter passes: feather first, blur second. This is intentionally a small deterministic kernel contract rather than a Photoshop-specific implementation. A future higher-quality kernel may replace the numerical kernel only through a new explicit contract and regression suite; the operation ordering remains stable.

## Explicitly deferred

This phase does not add a registry/plugin abstraction, GPU path, mask pixel serialization, or asset-resolution/storage ownership. `source_asset_id` remains resolved by the caller; `process_mask` accepts only the already materialized `RenderMask`.
