# Phase 6.5 — Layer Editing Surface Contract

## Scope

Expose explicit application editing commands over the existing immutable LayerStack without moving pixel ownership into the domain model or introducing a registry, plugin system, scheduler, or new persistence schema.

## Contract

1. Layer editing commands operate only through ProjectState and return a new ProjectState with exactly one revision increment.
2. Every command is immutable and validates all inputs before constructing the next state.
3. Add requires a LayerState with a unique layer_id and respects LayerStack.max_layers.
4. Remove requires an existing layer_id and preserves the identity and state of every remaining layer.
5. Duplicate creates a new explicit layer identity while preserving the source asset reference and layer properties; the new identity must never be inferred from object identity, process state, or randomness.
6. Reorder operates on explicit source and target indexes and preserves layer identities and payloads.
7. Visibility updates accept only bool values.
8. Opacity updates accept finite numeric values in [0, 1] and reject bool, NaN, and Infinity.
9. Blend-mode updates accept only LayerBlendMode values.
10. All layer operations preserve max_layers and unrelated ProjectState fields.
11. Invalid operations fail before mutation or revision creation.
12. Existing ReplaceLayerStackCommand behavior remains backward compatible.
13. No command performs filesystem, network, media decoding, rendering, or Telegram work.
14. Layer source_asset_id remains a reference only; command execution does not take ownership of pixel storage.
15. Deterministic operations produce identical canonical ProjectState for equivalent explicit inputs.
16. No hidden global state, global registry, plugin discovery, or implicit layer ordering is introduced.

## Adversarial test obligations

- duplicate layer identity on add;
- max-layer boundary and one-over rejection;
- unknown layer removal/update;
- source/target index boundaries;
- bool/non-numeric/non-finite opacity;
- invalid visibility and blend mode;
- duplicate produces a distinct explicit UUID and preserves all non-identity properties;
- failed command leaves editor state and revision unchanged;
- exactly one revision per successful command;
- undo/redo compatibility through existing ProjectEditor/CommandHistory;
- canonical round-trip determinism;
- mutation/aliasing attempts against returned layer stacks;
- preservation of unrelated ProjectState fields.

## Non-goals

- rendering algorithm changes;
- timeline orchestration;
- typography/layout primitives;
- persistence schema changes;
- AI providers;
- Telegram/UI integration;
- global capability registry;
- plugin framework.

## Gates

Contract -> adversarial tests -> minimal implementation -> local compile/lint/tests -> CI -> CodeQL -> adversarial review -> architecture review -> merge -> post-merge verification.
