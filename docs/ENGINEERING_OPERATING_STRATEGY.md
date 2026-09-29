# Engineering Operating Strategy

## Purpose

This document is the permanent engineering operating strategy for Ai-gif-studio3.

The project is evolving from a Telegram GIF/video pipeline into a lightweight, production-grade, non-destructive visual design and motion engine. The goal is not to clone Photoshop or Canva internally, but to provide professional editing capabilities while preserving a small, explicit architecture.

## Core operating rule

No Code Without Contract.

Every substantial capability follows:

Contract
-> Adversarial Tests
-> Implementation
-> Local verification
-> CI
-> CodeQL
-> Adversarial Engineering Review
-> Architecture Review
-> Merge

A green CI run is evidence, not the definition of correctness.

## Proactive engineering mandate

Engineering work must be proactive rather than purely request-driven.

For every proposed feature, review:

- API and domain contracts
- ownership and mutation semantics
- numerical boundaries and stability
- deterministic behavior
- backward compatibility
- resource admission, reservation and release
- cancellation and failure semantics
- concurrency implications
- security implications
- performance and peak memory
- test quality and adversarial coverage
- architecture drift and accidental abstractions
- missing adjacent capabilities that could otherwise force a later breaking redesign

If the requested step is not the safest or most valuable next step, stop and identify the better sequence before implementation.

## Architecture principles

Prefer:

RenderBuffer
-> explicit image operation
-> explicit Effect/command contract
-> EffectStack / compositor
-> Revision Graph
-> UI / Telegram workflow

Do not introduce registries, plugin systems, mega base classes, generic algorithm frameworks, or speculative abstractions unless a concrete current contract demonstrates the need.

Correct existing APIs must not be weakened or distorted to satisfy incorrect tests. Fix the test when the test violates the actual contract.

## Render correctness

Every image operation must explicitly define:

- color space
- alpha semantics
- input dtype and shape
- valid numeric domain
- output dtype and shape
- ownership
- mutation behavior
- boundary/interpolation policy
- deterministic behavior
- failure behavior
- reconstruction/identity invariants where applicable

HDR support must never be destroyed by accidental [0,1] clipping.

## Resource correctness

Heavy operations must provide a conservative peak-memory estimate and use ResourceManager admission/reservation/release semantics.

Do not use arbitrary RAM percentages, gc/del timing, or implicit allocation failure as resource policy.

Operations that can become expensive must define bounded work, cancellation behavior, and explicit resource-limit failures.

## Adversarial engineering

For each feature, attack:

- NaN and Inf
- negative and extreme values
- empty/minimal/maximal geometry
- alpha-zero and partially transparent pixels
- HDR values
- boundary coordinates
- aliasing and mutation
- repeated execution
- serialization/deserialization
- deterministic replay
- malformed input
- resource exhaustion
- cancellation
- concurrency
- backward compatibility

The review asks not only "does it work?" but "how can this fail silently?"

## External AI and research review

Recommendations from Gemini, Claude, web research, papers, libraries, or other agents are treated as external technical input, not specifications.

For every external proposal:

1. extract the valid mathematical/engineering insight;
2. verify it against the existing project contracts;
3. reject incorrect terminology or assumptions;
4. identify dependency and operational cost;
5. convert accepted ideas into explicit contracts;
6. write adversarial tests;
7. implement only after reconciliation.

Do not copy prototype code directly into production.

## Current advanced capability roadmap

The following capabilities are candidates, not permission to implement them immediately:

1. Frequency separation / high-low frequency retouching
2. 3D LUT and adjustment operations
3. Mesh/liquify/puppet-style warping
4. Smart selection / graph-cut segmentation
5. Content-aware fill / PatchMatch
6. Layer masks and vector masks
7. Curves, levels, exposure, hue/saturation, color balance and gradient-map adjustments
8. Blend/opacity/compositing refinements
9. Non-destructive smart-object-like source preservation
10. Perspective, skew, distort, free-transform and reference-point transforms
11. Text/type layers with editable typography
12. Vector shape/path primitives
13. Timeline/keyframe animation for transform, opacity and style
14. Frame animation utilities, tweening and onion-skin-style workflows
15. Motion/easing primitives
16. Auto-crop, perspective correction and content-aware expansion
17. Background removal, object selection and mask refinement
18. Clone/healing/patch retouch operations
19. Shadows, glows, strokes and other layer-style effects
20. Depth-aware effects such as bokeh/depth-of-field when a reliable depth source exists
21. Lens/distortion correction
22. HDR tone mapping and explicit color-management pipeline
23. AI-assisted editing as isolated, resource-bounded operations rather than architectural dependencies
24. Multi-format resize/export presets and adaptive composition
25. Template/preset systems only after the underlying editing contracts are stable

The roadmap is intentionally broader than the current implementation. Features enter the implementation queue only after dependency and contract analysis.

## Animation direction

The project should evolve from frame/GIF generation toward editable motion:

Layer/object properties
-> keyframes
-> deterministic interpolation/easing
-> timeline/revision integration
-> render sampling
-> export

The timeline must remain compatible with the non-destructive Revision Graph instead of becoming a second independent state system.

## Feature-selection rule

A feature is prioritized when it:

- provides substantial creative control;
- composes cleanly with existing contracts;
- can be implemented deterministically;
- has bounded resource behavior;
- can be tested adversarially;
- avoids premature framework abstractions;
- reduces future architectural lock-in.

## Known high-value capability families

### Professional image editing

- masks
- adjustment layers
- curves/levels/exposure
- LUTs
- selective color
- gradient maps
- healing/clone
- content-aware operations
- perspective and warp
- vector paths/shapes
- editable typography
- layer styles

### Motion/design editing

- keyframes
- easing
- transform animation
- opacity/style animation
- timeline composition
- frame utilities
- motion presets
- beat/snap alignment where the audio pipeline eventually supports it

### AI-assisted editing

- background removal
- object selection
- object isolation/repositioning
- erase/replace
- generative expansion
- segmentation-assisted masks
- AI enhancement/upscaling

AI capabilities must remain optional boundaries. The core renderer must not become dependent on a single model provider.

## Research-derived feature observations

Current Photoshop documentation demonstrates the importance of adjustment layers, Smart Objects, Smart Filters, layer masks, non-destructive cropping, editable type/shape layers, transformations, Puppet Warp, and timeline/keyframe animation. Canva documentation and product material additionally demonstrate the value of background removal, object isolation/repositioning, image-to-video, automatic resizing, generative editing, and conversion of flat imagery into editable layers.

These observations inform capability discovery, not a requirement to copy either product.

## Current implementation discipline

Do not implement the entire roadmap as a batch.

Use vertical slices. Each slice must be complete enough to be trusted:

contract -> tests -> implementation -> gates -> adversarial review -> merge.

When multiple tasks are truly independent, they may be batched, but dependencies and gate boundaries must remain explicit.

## Definition of "professional"

Professional does not mean maximum feature count.

It means:

- explicit contracts
- mathematically correct operations
- deterministic outputs
- safe ownership
- bounded resources
- reversible editing
- stable serialization
- strong tests
- clear failure semantics
- maintainable architecture
- measured performance
- no hidden state
- no accidental data loss

## Permanent review question

Before accepting any architectural change, ask:

"Does this make the editor more capable without making the engine less understandable, less deterministic, less safe, or harder to evolve?"

If the answer is unclear, investigate before merging.

## Execution command semantics

The commands **نفّذ / استمر / أكمل** are authorization to continue execution, not a request to wait for another micro-decision.

When one of these commands is given:

1. inspect the current repository state, active branch/PR/CI state, contracts, tests, and known blockers;
2. determine the next engineering step that best protects the project's correctness, architecture, and long-term progress;
3. execute that step rather than asking the user to choose between routine engineering alternatives;
4. if the user's suggested direction conflicts with a stronger architectural or correctness requirement, follow the safer/correct engineering sequence and document the reason;
5. batch genuinely independent work when this reduces cycle time, while preserving Contract -> Tests -> Implementation -> Verification gates;
6. never interpret "continue" as permission to bypass tests, CI, CodeQL, adversarial review, ownership checks, resource checks, or merge gates;
7. do not declare success merely because code was written or a workflow started; success requires observed evidence from the relevant gates.

The user delegates routine project steering through these commands. The assistant therefore owns the execution sequence within the agreed engineering strategy, while preserving the user's final authority over consequential product-direction changes.

## Project non-negotiables

The project operates under a simple objective:

- no avoidable correctness errors;
- no silent architectural regressions;
- no premature feature abandonment;
- no fake-green verification;
- no data-loss-prone behavior;
- no uncontrolled resource failures;
- no unnecessary architectural debt;
- no stopping merely because the next step was not explicitly spelled out.

This is not a promise that defects are mathematically impossible. It is a requirement that every discovered defect becomes an actionable engineering item, is isolated at its root, is verified by evidence, and is not knowingly carried forward as if it were acceptable.

## Continuity rule

The default state after a completed engineering step is **identify the next correct step and continue**, not stop and wait.

Continuation is subject to real blockers. A blocker means a condition that makes further implementation unsafe or invalid—for example, a broken contract, unresolved ownership ambiguity, failed critical test, security issue, unavailable required dependency, or missing decision that materially changes the architecture.

When blocked, the assistant should:
- isolate the blocker;
- fix it if it is within the existing engineering authority;
- otherwise state exactly what decision or external input is required;
- avoid unrelated speculative work merely to appear busy.

The target is sustained, evidence-driven progress with zero tolerance for knowingly ignoring defects—not pretending that defects can never occur.

