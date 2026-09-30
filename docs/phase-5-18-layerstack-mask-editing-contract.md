# Phase 5.18 LayerStack Mask Editing Contract

## Contract

LayerStack exposes `update_mask(layer_id, mask)` as the immutable integration boundary for editing an already-attached MaskState.

The operation:
- requires an existing layer and an existing mask on that layer;
- requires the replacement value to be a MaskState;
- preserves the layer ID, layer source asset ID, layer order, and all unrelated layer state;
- preserves the existing mask_id and source_asset_id;
- returns a new LayerStack without mutating the previous stack.

Changing mask identity or source identity is rejected. Mask removal remains the responsibility of `set_mask(layer_id, None)`; source replacement is a separate contract.

## Tests

The contract covers:
- successful immutable mask updates;
- preservation of mask/source identity;
- missing-mask rejection;
- type rejection;
- mask identity mismatch;
- source identity mismatch;
- unknown-layer behavior;
- previous-stack immutability and unrelated-layer isolation.

## Deferred

Command history, UI commands, source-asset replacement, and procedural/vector masks remain separate contracts.
