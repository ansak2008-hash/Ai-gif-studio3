# Phase 5.8 — Layer Render Binding Contract

## Objective

Bridge the immutable domain `LayerStack` to the existing temporal compositor without moving pixel ownership into the domain model.

Architecture:

`ProjectState.layer_stack -> LayerStack -> LayerRenderBinding -> BlendLayer -> temporal compositor`

## Scope

Phase 5.8 owns only the explicit adapter boundary that translates layer state into compositor-ready `BlendLayer` values.

Requirements:

- Preserve `LayerStack` back-to-front ordering exactly.
- Skip invisible layers deterministically.
- Resolve `source_asset_id` through a caller-owned mapping of UUID to `RenderBuffer`.
- Never copy or mutate source buffers during binding.
- Apply layer opacity through the existing `RenderMask` contract.
- Omit the mask when opacity is exactly 1.0.
- Preserve the existing compositor's `BlendLayer` and `BlendMode.NORMAL` semantics.
- Validate the complete binding input before producing the returned tuple.
- Missing source assets fail closed with a deterministic `KeyError`.
- Reject invalid mapping values before any returned binding is produced.
- Return an immutable detached tuple.
- No filesystem, database, network, global registry, plugin framework, media decoding, or rendering kernel.
- Do not change `RenderBuffer`, `RenderMask`, `BlendLayer`, or compositor numerical formulas.

## Determinism and Ownership

Equivalent `LayerStack` and equivalent source mapping produce equivalent binding order and opacity masks.

The adapter does not own source pixel bytes. It only references caller-owned `RenderBuffer` instances.

## Non-goals

- Asset storage/catalog/registry.
- Media decoding or encoding.
- Blend-mode editing beyond the existing NORMAL compositor path.
- Timeline/keyframes.
- UI/Telegram integration.
- Persistence format changes.
- GPU acceleration.

## Gates

Contract -> adversarial tests -> implementation -> architecture review -> unit/integration/determinism/security/Ruff -> CodeQL -> final adversarial audit -> merge -> post-merge CI/CodeQL verification.
