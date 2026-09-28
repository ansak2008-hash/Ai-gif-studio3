# Creative Transformation Roadmap

Status: **active product roadmap**

The six-phase temporal rendering foundation is complete. The next product track expands the
studio from a GIF renderer into a deterministic creative transformation platform.

## Design target

The product should combine:
- Photoshop-class deterministic pixel operations and compositing primitives.
- Canva-class reusable design, typography, layout, presets, and workflow composition.
- AI-native transformations behind explicit provider/model gates.
- High-quality temporal rendering, PBR surfaces, camera motion, and GIF/video export.
- A single typed capability/workflow system so every tool is discoverable, validated, testable,
  and composable rather than implemented as isolated UI features.

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

Next:
- crop/fit/fill policies as reusable transforms
- affine/perspective transforms
- color curves and LUT-style grading (Phase 4.11 foundation: deterministic tone curves)
- blend modes and masks (Phase 4.12 foundation: deterministic binary blending with canonical masks)
- layer compositing
- selective region transforms

### Track B — Design and motion
Existing foundation:
- composition
- typography
- frames
- backgrounds
- presets
- motion
- PBR manuscript rendering
- linear-light export

Next:
- reusable effect stacks
- keyframed transform parameters
- per-layer motion
- temporal effects
- richer transitions

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

AI capabilities must return typed validated results and must never be marked production-ready
merely because a provider endpoint exists.

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
