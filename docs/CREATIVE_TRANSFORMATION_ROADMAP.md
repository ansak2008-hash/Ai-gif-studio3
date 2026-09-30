# Creative Transformation Roadmap

Status: **active product roadmap**

The deterministic temporal rendering foundation has been extended through Phase 4.22, and the project has established an immutable editing/revision foundation through Phase 5. The next product track expands the studio from a GIF renderer into a deterministic creative transformation platform and professional design editor.

## Design target

The product should combine:
- Photoshop-class deterministic pixel operations and compositing primitives.
- Canva-class reusable design, typography, layout, presets, and workflow composition.
- AI-native transformations behind explicit provider/model gates.
- High-quality temporal rendering, PBR surfaces, camera motion, and GIF/video export.
- A typed project/editing boundary so tools are discoverable, validated, testable, replayable, and composable rather than implemented as isolated UI features.

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
- persistent mask lifecycle and editing contracts (Phase 5.13–5.20)
- deterministic project/revision persistence foundations (Phase 5.1–5.5)

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
- temporal scene/layer orchestration when an end-to-end frame composition contract is required
- additional transition primitives only where concrete product requirements justify them
- editor-facing composition and timeline operations built on the immutable project boundary

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

Foundation:
- immutable project state
- immutable commands
- revision graph
- canonical persistence
- crash-safe recovery
- layer state and render binding
- mask state, processing, source extraction, editing, persistence, and lifecycle audit
- project editor boundary (Phase 6.1)

Planned sequence:
1. **Phase 6.1 — Project Editor Boundary**
   - One application boundary over ProjectState, ProjectCommand, RevisionGraph, and canonical persistence.
   - Atomic command execution.
   - Immutable checkout and branching.
   - Deterministic canonical save/load.
   - No registry/plugin/runtime dependency introduced.
2. **Phase 6.2 — Execution and Concurrency Contract**
   - Define ownership, serialization, admission, cancellation, and isolation rules before parallel editor/render execution.
   - Establish deterministic behavior under concurrent requests.
3. **Phase 6.3 — Capability Contract**
   - Typed capability descriptors and compatibility validation.
   - No premature global registry or plugin framework.
   - Every future editor operation must expose explicit input/output/domain/boundary contracts.
4. **Phase 6.4 — Deterministic Workflow / Replay**
   - Immutable operation sequences.
   - Canonical workflow serialization.
   - Replay equivalence and failure containment.
5. **Phase 6.5 — Layer Editing Surface**
   - Add/remove/duplicate/reorder layers.
   - Visibility, opacity, transforms, blend/mask integration.
   - Preserve layer identity and immutable revision semantics.
6. **Phase 6.6 — Design Primitives**
   - Typography, alignment, guides, frames, backgrounds, reusable layout primitives, and composition constraints.
7. **Phase 6.7 — Timeline / Temporal Composition**
   - Connect project revisions and layer state to deterministic time-sampled composition.
   - Preserve existing temporal engine contracts.
8. **Phase 6.8 — Presets / Variants / Export Profiles**
   - Versioned reusable design intent.
   - Batch variants and explicit export policies.
9. **Phase 6.9 — AI Capability Boundary**
   - Provider/model provenance.
   - Typed inputs/outputs.
   - Deterministic validation and explicit non-production states until provenance gates pass.

The sequence is deliberately foundational: editor state and execution semantics precede feature multiplication.

### Track E — Platform hardening and quality

Continuous:
- Contract -> Tests -> Implementation -> CI/CodeQL -> performance verification -> adversarial review -> merge.
- Exact-HEAD verification before declaring a gate successful.
- Ownership and mutation audits for every new mutable boundary.
- Determinism checks where the operation is expected to be deterministic.
- Numerical-domain and finite-value validation at public boundaries.
- Resource admission/reservation/release with explicit ownership and finally-based release.
- No speculative algorithm or runtime dependency without complexity, memory, dependency, numerical-domain, determinism, benchmark, and adversarial justification.
- No placeholder success responses for production capabilities.
- No broad formatting churn solely to satisfy a newly introduced gate.

## Engineering gates

Every new capability must:
1. have a typed contract;
2. have deterministic/boundary tests where determinism is meaningful;
3. integrate through the project/editor boundary when applicable;
4. avoid new runtime dependencies unless explicitly justified;
5. preserve existing Phase 2 contracts and the legacy renderer boundary;
6. pass Ruff, unit, integration, load, and determinism CI gates when applicable;
7. receive adversarial review before merge;
8. preserve backward-compatible persistence semantics or include an explicit migration contract.

## Explicit non-goals

The roadmap does not authorize:
- premature registries/plugins;
- speculative "professional" algorithms without a bounded contract and benchmark;
- unverified AI/model providers;
- replacing correct APIs merely to satisfy incorrect tests;
- claiming production readiness from CI alone;
- reopening completed phases without a concrete regression or contract reason.

The roadmap prioritizes real working transformations and a durable editor foundation over feature-count inflation.
