# Phase 4.19 — Per-Layer Motion
## Objective
Add immutable per-layer affine motion without creating a second renderer, timeline, or layer model.
## Interface
- MotionLayer(source, track, mode, mask) binds one canonical RenderBuffer to an existing AffineTransformTrack.
- MotionLayer.sample(time) returns an existing BlendLayer containing the transformed source and preserved blend/mask configuration.
- Sampling uses the existing AffineTransformEffect and AffineTransformSpec boundaries.
## Canonical call
MotionLayer.sample(0.5)
## Preconditions
- Source is a canonical RenderBuffer.
- Track is an AffineTransformTrack.
- Source dimensions equal the track target dimensions.
- Optional mask is a RenderMask with matching source dimensions.
- Blend mode is an existing BlendMode.
- Sample time is finite and satisfies the existing track contract.
## Postconditions
- Returned value is an existing BlendLayer.
- Transformed source is a newly owned RenderBuffer.
- Blend mode and mask are preserved.
- Source, track, and mask are not mutated.
- Sampling is deterministic.
## Architectural integration
MotionLayer is a thin binding between the existing keyframed affine parameter sampler, affine renderer, and compositor layer contract. It does not own current-time state and does not introduce a new timeline, registry, graph, serialization format, or rendering backend.
## Non-goals
- No per-layer opacity abstraction.
- No translation/rotation/scale schema separate from affine matrices.
- No layer graph or scene model.
- No serialization or persistence.
- No GPU path or new runtime dependency.
- No changes to existing BlendLayer or AnimationTimeline semantics.
