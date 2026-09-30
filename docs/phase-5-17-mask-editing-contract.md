# Phase 5.17 Mask Editing Contract

## Contract

MaskState remains immutable persistent state. Editing operations return a new validated MaskState; they never mutate the existing state.

Supported operations:

- with_enabled(bool)
- with_inverted(bool)
- with_opacity(0..1)
- with_feather_radius(0..4096)
- with_blur_radius(0..4096)
- with_levels(low, high) where 0 <= low < high <= 1
- with_threshold(float | None) where a numeric threshold is in [0, 1]; None disables thresholding

The mask identity (mask_id) and source identity (source_asset_id) are preserved by every edit. Source replacement is deliberately not part of this editing contract because it changes asset identity rather than mask parameters.

## Validation

All edits pass through the existing constructor validation. Boolean values are not accepted as numeric parameters, non-finite values are rejected, and ranges remain unchanged.

## Ownership and determinism

No mutable state is shared between the original and edited object. Canonical JSON remains deterministic, and an edit chain can be serialized and reconstructed without changing its state.

## Deferred

Layer-stack command history integration, UI/editor commands, source-asset replacement, and procedural/vector mask editing remain separate contracts.
