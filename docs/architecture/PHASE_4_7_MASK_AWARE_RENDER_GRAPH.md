# Phase 4.7 — Mask-Aware Render Graph Contract

## Objective

Connect the canonical RenderMask to RenderGraph through a generic, reusable node contract for selective processing.

The phase must allow future effects such as blur, glow, color adjustment, distortion, and other unary transforms to share one masking mechanism instead of implementing mask blending independently.

## Contract

A RenderNode may optionally declare a RenderMask.

When a node has a mask:

1. The node must be a unary render stage:
   - zero dependencies means the graph's initial RenderBuffer is the source;
   - one dependency means that dependency is the source;
   - more than one dependency is rejected because the mask needs an unambiguous source baseline.
2. The node's existing process callable runs normally against the source.
3. The processed result is selectively applied against the source in canonical linear RGBA space:
   - output = source * (1 - mask) + processed * mask
4. The mask must have exactly the same spatial dimensions as the source.
5. The mask is scalar coverage/control data in [0, 1]; no resampling, clamping, color conversion, premultiplication, or implicit geometry change is allowed.
6. mask=0 must reproduce the source exactly.
7. mask=1 must reproduce the node's processed result exactly.
8. Intermediate mask values must interpolate deterministically per RGBA channel.
9. The source and processed buffers must not be mutated or aliased by the resulting output.
10. The resulting value must remain a canonical RenderBuffer.
11. Existing unmasked RenderNode and RenderGraph behavior remains unchanged.
12. Runtime node errors remain observable; masking must not swallow exceptions.

## Why this design

Adding a generic optional mask to RenderNode keeps the graph topology unchanged while making selective processing a first-class graph concern. Future unary effects can opt into the same contract without duplicating mask arithmetic.

A separate mask-aware graph type was rejected because it would duplicate graph validation, execution ordering, and output invariants.

Masking is intentionally limited to unary nodes. Applying one scalar mask to a fan-in node would require an explicit definition of which dependency represents the unmodified baseline. That ambiguity is deferred until a dedicated multi-input compositing/masking contract is required.

## Alpha semantics

Masking operates on canonical straight-alpha linear RGBA values and linearly interpolates all four channels. It does not silently convert the public RenderBuffer representation to premultiplied alpha.

## Non-goals

Phase 4.7 does not add:

- effect implementations;
- automatic mask generation;
- mask resampling;
- GPU execution;
- color-management changes;
- graph mutation at runtime;
- temporal/frame-stack masking;
- multi-input masked nodes;
- plugin APIs.

## Sequence

Contract → Tests → Implementation → CI → Adversarial Review → Merge.
