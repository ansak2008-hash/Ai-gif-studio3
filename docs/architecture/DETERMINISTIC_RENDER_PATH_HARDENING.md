# Deterministic Render Path Hardening Contract

## Scope
Harden the existing AnimationTimeline timing boundary used by rendering/export. This phase does not change render kernels, motion formulas, color conversion, or GIF encoding.

## Contract
1. Timeline construction rejects bool/non-numeric, non-finite, and non-positive duration/fps values.
2. Frame count is derived deterministically from the exact validated duration/fps product and is stable across repeated calls.
3. Frame timestamps are generated from integer frame indices and a single deterministic duration/frame-count rule; repeated calls are byte-for-byte/value-for-value identical.
4. Timestamps are monotonic, start at zero, and remain strictly before total duration.
5. Centisecond delay allocation is deterministic, positive for every frame, sums exactly to total duration in centiseconds, and differs by at most one centisecond where feasible.
6. A timeline cannot silently accept a duration that rounds to zero centiseconds or a frame count that cannot receive one centisecond per frame.
7. Loop progress is deterministic for finite input; non-loop progress clamps to [0,1].
8. No wall-clock state, global mutable state, random state, filesystem, or network state participates in timing.
9. Existing public AnimationTimeline/FrameTiming APIs remain compatible.

## Adversarial tests
- bool and invalid numeric constructor inputs;
- repeated frame_times/timings equality;
- monotonic/bounded timestamps;
- fractional frame-count boundary stability;
- minimum-duration/centisecond boundary;
- exact delay sum and spread;
- loop wrap and non-loop clamping;
- no mutation of timeline state.

## Non-goals
No render-kernel changes, no motion interpolation changes, no color/GIF encoder changes, no new scheduler/registry abstraction.

## Gates
Contract -> adversarial tests -> minimal implementation -> unit/integration/determinism/security/Ruff -> CodeQL -> adversarial review -> merge.
