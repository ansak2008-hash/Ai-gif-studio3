# Phase 5.16 Mask Source Contract

## Contract

Mask pixels are created explicitly from an already materialized `RenderBuffer`; no global asset registry or hidden lookup is introduced.

Two deterministic source projections are supported:

- `mask_from_alpha(RenderBuffer)`: extracts the buffer's linear alpha channel exactly.
- `mask_from_luminance(RenderBuffer)`: computes linear-light Rec.709 luminance using coefficients `0.2126, 0.7152, 0.0722`, ignores alpha, then clamps the result to `[0, 1]`.

Both functions:
- require a canonical `RenderBuffer`;
- never mutate or retain ownership of the source buffer;
- return an owned read-only float32 `RenderMask`;
- are deterministic for the same source pixels.

HDR RGB is allowed by the `RenderBuffer` contract. Because `RenderMask` is a normalized control field, luminance above `1.0` is clamped at this boundary rather than rejected or allowed to violate the mask range.

## Architectural boundary

`MaskState.source_asset_id` remains a persistent reference only. Asset resolution remains explicit in the caller-owned `masks` mapping used by `bind_layer_stack()`.

This phase deliberately does not introduce a registry, plugin abstraction, storage service, or implicit asset discovery.

## Security and ownership

The source is validated by the existing `RenderBuffer` contract. The mask constructors copy through the canonical `RenderMask` boundary, so later source-buffer changes cannot mutate the derived mask.

## Deferred

Procedural masks, vector/path masks, text-derived masks, animated mask assets, and GPU implementations remain separate contracts.