# Phase 4.20 — Temporal Effects
## Objective
Add a minimal deterministic time-sampled effect primitive without introducing renderer-owned time state or a second timeline system.
## Interface
- TemporalFadeEffect(start_time, end_time, start_alpha, end_alpha) defines one immutable alpha ramp.
- effect((source,), time) returns a new RenderBuffer.
- Progress is linearly interpolated and clamped to the declared interval.
## Canonical call
effect((source,), 0.5)
## Preconditions
- Source is a canonical RenderBuffer.
- Time and effect parameters are finite.
- end_time is greater than start_time.
- Alpha endpoints are within [0, 1].
## Postconditions
- Output is a new canonical RenderBuffer with unchanged RGB and alpha multiplied by the sampled ramp.
- Input storage is not mutated.
- Sampling is deterministic.
## Architectural integration
The effect receives time explicitly and remains stateless. It can be composed around existing RenderBuffer effects without changing AnimationTimeline, EffectStack, MotionLayer, or compositor contracts.
## Non-goals
- No implicit current-time state.
- No timeline ownership or frame scheduling.
- No easing registry or dynamic dispatch.
- No keyframe collection; keyframed parameter sampling remains in AffineTransformTrack.
- No layer graph, serialization, GPU path, or runtime dependency.
