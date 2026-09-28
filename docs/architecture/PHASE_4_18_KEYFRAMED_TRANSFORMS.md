# Phase 4.18 — Keyframed Transform Parameters
## Objective
Add immutable, deterministic keyframed affine-transform parameter sampling without creating a second timeline system.
## Interface
- `AffineTransformKeyframe(time, matrix)` stores one finite 2x3 affine matrix at a strictly ordered time.
- `AffineTransformTrack(keyframes)` owns an immutable ordered tuple of keyframes.
- `track.sample(time)` returns a new `AffineTransformSpec` at the sampled time.
- Sampling linearly interpolates each affine matrix parameter between adjacent keyframes.
- Sampling outside the keyframe range clamps to the first or last keyframe.
## Canonical call
`track.sample(0.5)`
## Preconditions
- At least two keyframes.
- Times are finite and strictly increasing.
- Matrices are finite numeric 2x3 affine matrices with non-degenerate linear components.
- Sample time is finite.
## Postconditions
- Returned value is a validated `AffineTransformSpec`.
- Returned matrix is owned and read-only through the existing spec contract.
- Keyframe inputs and track configuration are not mutated.
- Sampling is deterministic.
## Architectural integration
The track reuses the existing `AffineTransformSpec` boundary and affine geometry semantics. It is a parameter sampler, not a renderer and not a new timeline/curve registry. Existing `Keyframe`/`MotionCurve` remain unchanged because their scalar loop and rotation semantics are not appropriate for affine matrix parameters.
## Non-goals
- No per-layer motion.
- No frame rendering or implicit current-time state.
- No serialization or persistence.
- No registry or dynamic dispatch.
- No GPU path or new runtime dependency.
