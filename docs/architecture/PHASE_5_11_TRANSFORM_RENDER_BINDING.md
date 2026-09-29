# Phase 5.11 — Transform-to-Render Binding

## Objective
Make the existing immutable Phase 5.6 Crop/Scale/Translate state executable against the existing canonical RenderBuffer without creating a renderer, registry, or new transform math framework.

## Contract
ProjectState.transform is a project-canvas transform applied to one canonical RenderBuffer after the caller has resolved/composited project content.

1. Crop coordinates are canvas coordinates in the existing 320x320 project space.
2. Crop `(x, y, width, height)` selects an explicit source rectangle. The resulting buffer dimensions are exactly `(width, height)`.
3. Scale is applied around the center of the cropped canvas.
4. Translation is applied in output-canvas pixel coordinates after scaling.
5. Output dimensions remain exactly the crop dimensions.
6. Areas outside the transformed source are transparent RGBA zero.
7. The adapter is pure: it never mutates or takes ownership of the input RenderBuffer.
8. The adapter reuses the existing AffineTransformEffect and RenderBuffer contracts; it does not duplicate warp math.
9. Identity TransformState returns an equivalent detached RenderBuffer, not the caller-owned buffer.
10. Transform application is deterministic for identical input/state.
11. Invalid state is rejected by TransformState before rendering.
12. No filesystem, network, persistence, UI, timeline, GPU, registry, or plugin dependency is introduced.

## Numerical policy
- Matrix construction uses float64.
- Rendering continues through the existing OpenCV linear interpolation policy of AffineTransformEffect.
- No implicit clipping or color conversion is introduced.
- Alpha remains part of canonical linear RGBA.

## Gates
Contract -> adversarial tests -> minimal adapter implementation -> architecture/adversarial review -> unit/integration/determinism/security/Ruff -> CodeQL -> post-merge verification.
