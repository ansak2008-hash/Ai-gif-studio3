# Phase 5.9 — Layer Blend Mode State Contract

## Objective
Extend immutable domain layer state with an explicit, rendering-independent blend-mode value so the existing compositor can consume layer blend intent without coupling the domain to temporal-engine implementation types.

## Architecture
`ProjectState.layer_stack -> LayerStack/LayerState -> LayerRenderBinding -> BlendLayer -> temporal compositor`

The domain owns the serialized semantic value. The temporal adapter translates that value to the existing `BlendMode` enum.

## Requirements
- `LayerBlendMode` is a closed string enum with exactly the currently supported semantic values: `normal`, `multiply`, `screen`, `overlay`.
- `LayerState.blend_mode` defaults to `normal`.
- Layer state remains immutable and slot-based.
- Invalid blend-mode values are rejected before any new stack is returned.
- `LayerStack.set_blend_mode(layer_id, mode)` returns a new immutable snapshot.
- Existing add/remove/move/visibility/opacity operations preserve blend mode.
- Canonical JSON includes `blend_mode`; old layer JSON without it is rejected rather than silently changing semantics.
- ProjectState canonical round-trip and CommandHistory continue to preserve the complete layer state.
- LayerRenderBinding maps the domain mode to the existing temporal `BlendMode` without changing compositor formulas.
- Binding remains deterministic, ordered, non-owning, and validates all visible sources before creating output.
- No registry, plugin system, filesystem, database, media decoder, or new rendering abstraction.

## Non-goals
- New blend formulas.
- Changes to `BlendModeEffect`, `BlendLayer`, or compositor math.
- Asset storage or lifecycle.
- UI/Telegram integration.
- Timeline/keyframes.
- Nested layer groups.

## Gates
Contract -> adversarial tests -> implementation -> architecture review -> unit/integration/determinism/Ruff -> CodeQL -> post-merge verification.
