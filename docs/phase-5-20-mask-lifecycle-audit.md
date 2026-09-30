# Phase 5.20 — Mask Lifecycle Adversarial Audit

## Contract
Audit the complete persistent mask lifecycle without introducing a new abstraction:
- create/attach a mask with `LayerStack.set_mask`;
- edit an existing mask only through `LayerStack.update_mask`;
- remove a mask with `LayerStack.set_mask(layer_id, None)`;
- preserve layer identity, order, source identity, unrelated layer state, and `max_layers`;
- preserve `mask_id` and `source_asset_id` across immutable edits;
- reject mask identity/source replacement through `update_mask`;
- preserve masked state through canonical LayerStack JSON round-trip;
- continue accepting legacy LayerStack JSON with no mask field;
- fail closed for missing mask source, wrong mask type, and dimension mismatch at render binding;
- never mutate caller-owned source/mask data or prior immutable domain state;
- keep lifecycle transitions deterministic.

## Adversarial cases
The test suite explicitly covers:
1. attach → edit → serialize → restore → remove;
2. remove does not mutate the previous stack;
3. update cannot replace mask identity or source identity;
4. unknown layer and missing-mask transitions fail deterministically;
5. legacy unmasked LayerStack JSON remains readable;
6. restored masked state binds identically to an explicit RenderMask source;
7. missing/wrong/dimension-mismatched mask sources fail closed;
8. caller-owned RenderMask data remains unchanged after binding.

## Gate
Contract → tests → implementation only if a test exposes a real contract defect. No registry, plugin system, hidden asset lookup, or second mask representation is introduced.
