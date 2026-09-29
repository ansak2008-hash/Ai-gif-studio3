# Phase 5.12 — Rotation Editing Contract

## Objective

Extend the existing immutable transform boundary with deterministic rotation without introducing a new renderer, transform framework, registry, plugin layer, UI dependency, or storage adapter.

## Contract

1. TransformState.rotation is a finite degree value in the closed range [-360.0, 360.0].
2. The default rotation is 0.0 and preserves all existing Phase 5.6/5.11 canonical behavior.
3. RotateCommand(degrees) applies a delta to the current transform and increments ProjectState.revision exactly once when executed through CommandHistory.
4. Rotation is composed with the existing scale around the center of the current crop rectangle.
5. Translation remains an output-canvas pixel offset applied after scale and rotation.
6. Crop geometry remains authoritative: output dimensions are exactly the crop dimensions.
7. Areas outside the transformed source are transparent RGBA zero.
8. The transform binding remains pure and does not mutate or take ownership of its input RenderBuffer.
9. Existing AffineTransformEffect remains the only render primitive used for rotation.
10. Equivalent state/command inputs produce deterministic canonical JSON and identical rendered output.
11. Invalid rotation values are rejected at the domain boundary before rendering or mutation.
12. Existing canonical project states without a rotation field remain valid and decode as 0.0.
13. No filesystem, network, persistence adapter, UI, timeline, GPU, registry, or plugin dependency is introduced.

## Numerical policy

- Rotation matrix construction uses float64.
- OpenCV's existing affine interpolation policy remains unchanged.
- No implicit color-space conversion or alpha semantic change is introduced.

## Gates

Contract -> tests -> implementation -> adversarial review -> unit/integration/determinism/security/Ruff -> CodeQL -> final audit -> merge.