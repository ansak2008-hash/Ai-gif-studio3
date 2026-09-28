# Creative Transformation Roadmap

Status: **active product roadmap**

The deterministic temporal rendering foundation has been extended through Phase 4.22. The next product track expands the studio from a GIF renderer into a deterministic creative transformation platform.

## Design target

The product should combine:
- Photoshop-class deterministic pixel operations and compositing primitives.
- Canva-class reusable design, typography, layout, presets, and workflow composition.
- AI-native transformations behind explicit provider/model gates.
- High-quality temporal rendering, PBR surfaces, camera motion, and GIF/video export.
- A single typed capability/workflow system so every tool is discoverable, validated, testable, and composable rather than implemented as isolated UI features.

This is a capability target, not a claim that the product currently matches any named competitor.

## Capability tracks

### Track A — Deterministic transformations

Implemented:
- resize
- rotate
- horizontal/vertical flip
- brightness/contrast
- saturation
- grayscale
- sepia
- blur/sharpen
- vignette
- posterize
- pixelate
- RGB/RGBA support
- immutable ordered transform chains
- deterministic batch application
- crop/fit/fill policies (Phase 4.15 foundation: canonical linear RGBA framing)
- affine/perspective transforms (Phase 4.16 foundation: canonical linear RGBA geometry warps)
- color curves and LUT-style grading (Phase 4.11 foundation: deterministic tone curves)
- blend modes and masks (Phase 4.12 foundation: deterministic binary blending with canonical masks)
- layer compositing (Phase 4.13 foundation: typed deterministic blend-layer orchestration)
- selective region transforms (Phase 4.14 foundation: reusable typed masked unary-transform orchestration)

### Track B — Design and motion

Implemented:
- composition
- typography
- frames
- backgrounds
- presets
- motion
- PBR manuscript rendering
- linear-light export
- reusable effect stacks (Phase 4.17 foundation: immutable ordered RenderBuffer effect composition)
- keyframed affine transform parameters (Phase 4.18 foundation: deterministic parameter sampling)
- per-layer affine motion (Phase 4.19 foundation: time-sampled MotionLayer binding)
- temporal fade effects (Phase 4.20 foundation: explicit-time unary temporal effect)
- temporal effect stacks (Phase 4.21 foundation: immutable explicit-time unary effect composition)
- temporal crossfade transition (Phase 4.22 foundation: deterministic two-input transition)

Next:
- additional transition primitives only where concrete product requirements justify them
- temporal scene/layer orchestration when an end-to-end frame composition contract is required

### Track C — AI transformations

Provider/model gated until exact model code, weights, licenses, and SHA-256 provenance are verified:
- background removal
- background replacement
- object removal
- inpainting
- upscaling
- frame interpolation
- style transfer
- relighting
- generative expansion

AI capabilities must return typed validated results and must never be marked production-ready merely because a provider endpoint exists.

### Track D — Product composition

Next:
- project/revision graph
- undo/redo through immutable commands
- reusable transformation presets
- batch variants
- export profiles
- capability compatibility validation
- deterministic replay of a creative workflow

## Engineering gates

Every new capability must:
1. have a typed contract;
2. have deterministic/boundary tests where determinism is meaningful;
3. integrate through the capability/workflow boundary;
4. avoid new runtime dependencies unless explicitly justified;
5. preserve existing Phase 2 contracts and the legacy renderer boundary;
6. pass Ruff, unit, integration, load, and determinism CI gates when applicable.

The roadmap prioritizes real working transformations over placeholder feature flags.
