# AI GIF Studio — Claude Code Instructions

## Architecture
- `src/ai_gif_studio/temporal_engine/` contains the deterministic Video→GIF pipeline and the isolated Manuscript/PBR rendering foundation.
- Video→GIF and Manuscript Animation are separate features. NEVER mix their data flow, APIs, or rendering stages.
- Manuscript rendering uses the canonical camera, plane, SDF/bevel/depth, PBR, RenderBuffer, and compositor contracts.
- Do not introduce Gemini/DeepSeek runtime integrations. External engineering reports are input for human-reviewed changes only.
- The mandatory engineering process is defined in `docs/ENGINEERING_WORK_PROTOCOL.md`. Read and follow it for every substantial architectural change.
- Python formatting/import policy is defined in `docs/development/conventions.md`; Ruff is the source of truth.

## Current Engineering Direction

The repository is moving from the historical phase/batch layout toward an explicit contract-driven rendering architecture.

Current sequence:
1. Contract hardening
2. RenderBuffer contract
3. Compositor contract
4. Render Graph contract
5. Integration of existing PBR/multi-light capabilities
6. Masks/effects and color-management boundaries
7. Performance/GPU boundaries
8. API/UI/mobile integration

Existing capabilities should be composed through explicit boundaries rather than rewritten unnecessarily.

## Phase Status

Historical phases below describe the earlier project foundation. They do not override the current contract-driven rendering plan.

| Phase | Historical Status | Scope |
|---|---|---|
| 1 | Implemented | Perspective Camera + Manuscript Plane |
| 2 | Implemented / frozen | Canonical SDF + Bevel + Normals |
| 3 | Implemented / CI-verified | PBR Material + deterministic renderer integration |
| 4 | Implemented / CI-verified | Deterministic motion separation |
| 5 | Implemented / CI-verified | Linear-light color and GIF export expansion |
| 6 | Implemented / CI-verified | End-to-end manuscript pipeline |

## Core Product Output Requirements

The following requirements are adopted from the Photo/GIF product specification only where they strengthen or clarify the existing Ai GIF Studio contracts. They are product requirements, not permission to copy the old Photo architecture or dependency stack.

### Canonical output invariants

- Final design GIF canvas MUST be exactly 320x320.
- Hard output size MUST remain <= 2,400,000 bytes.
- Final GIF palette MUST contain no more than 256 colors.
- Lanczos remains the required resize filter where resizing is performed.
- Final GIF output MUST loop indefinitely (loop=0).
- Final delivery MUST not rely on GIF transparency; transparent intermediate assets may exist only when an explicit layer/render contract requires them.
- Default design background target is #0A0A0A unless an explicit background specification overrides it.
- Output admission MUST validate actual artifact properties after encoding; configuration values alone are not proof.
- Size, dimensions, palette, duration, frame-rate, loop metadata, and format constraints are artifact invariants whenever the active export contract requires them.

### Input boundary requirements

- User image inputs MUST be validated before entering the rendering domain.
- The design product target requires a minimum usable image size of 100x100 pixels; smaller inputs MUST be rejected explicitly rather than silently upscaled into an apparently valid source.
- Video inputs MUST be bounded by an explicit maximum input size and duration at the Telegram boundary. The current product target is 20 MB maximum input size and a 6-second processing window; longer video content MUST be clipped according to the active processing contract rather than allowed to expand unbounded work.
- Corrupt, unsupported, or malformed media MUST fail with a typed/explicit validation outcome and MUST NOT reach deep rendering stages as if valid.

### Composition model

The product composition model is layered and non-destructive. The intended conceptual order is:

1. background
2. avatar/image
3. frame
4. typography/manuscript
5. effects
6. particles/sparkles

The ordering is a product composition target, not a reason to introduce a generic layer registry. Existing typed LayerState, Effect, mask, compositor, and project/revision contracts remain authoritative.

### Visual quality invariants

When a feature claims professional GIF output, verification SHOULD cover, where objectively testable:

- no unexpected frame dimension changes;
- no malformed/empty frames;
- no abrupt timing discontinuities introduced by the renderer;
- source content is not unintentionally stretched or distorted;
- background behavior remains within the declared background contract;
- avatar/image framing remains within the declared geometry contract;
- final artifact is reusable independently of Telegram delivery success.

### Motion contract boundary

Motion behavior is part of the product contract but MUST remain explicit and deterministic. Supported motion families may include fade, scale, rotation, translation, pulse/glow, writing/reveal, character bounce, glow text, and shimmer when individually contracted. Easing families may include linear, ease-in, ease-out, ease-in-out, bounce, elastic, and back. Do not introduce all of these as an uncontracted batch; each implemented family requires its own domain contract, boundary tests, determinism semantics, and resource analysis.

### Reconciliation rule

The Photo specification is a product reference, not a replacement for existing Ai GIF Studio contracts. If it conflicts with an existing verified contract, the existing verified contract wins unless a deliberate change contract is approved.

In particular, do NOT copy its dependency versions, Telegram/Railway folder layout, Flask architecture, 10 FPS default, or any other implementation detail merely because it appears in the reference specification. Extract product invariants and useful boundary requirements only.

## Hard Rules

1. NEVER use `from X import *`.
2. NEVER use `warpAffine` for the Manuscript camera path. Use perspective projection + homography + `warpPerspective`.
3. NEVER use Sobel(alpha) as the source of Manuscript surface normals. Use the canonical SDF/bevel field.
4. NEVER add `random`, `time.time`, or unseeded `np.random` to a render path.
5. After edits, run `ruff check .` and `pytest -q -m "unit and not integration and not slow"` when the environment is available.
6. `cinematic_camera.py` is deprecated. Do not modify it; delete only as part of an explicit migration.
7. NEVER introduce a new runtime dependency without explicit approval.
8. Do not weaken mathematical/visual acceptance thresholds merely to make CI green.
9. Do not claim tests passed unless their output was actually observed.
10. Do not modify the Video→GIF pipeline while implementing Manuscript/PBR rendering features unless the change is explicitly required and isolated.
11. Do not bypass the Contract → Tests → Implementation → CI → Adversarial Review → Merge sequence for substantial changes.
12. Treat green CI and architectural fitness as separate gates.
13. Do not invent manual Ruff/isort spacing rules. Follow Ruff diagnostics and the repository convention document.

## File Ownership

- `temporal_engine/__init__.py`: explicit public API only; avoid broad/god exports.
- `render_buffer.py`: canonical owned float32 linear RGBA render storage and its contract.
- `compositor.py`: deterministic alpha compositing contract; preserve explicit alpha semantics.
- `bevel.py`: deterministic bevel profile and its closed-form derivative.
- `depth_field.py`: canonical signed distance field, height construction, and surface normals.
- `camera.py`: CameraState, CameraModel, and projection.
- `manuscript_plane.py`: ManuscriptPlane, projected corners, homography, and perspective warp.
- Existing PBR modules: reusable shading/material/light capabilities; prefer orchestration over duplication.

## Test Conventions

- Unit tests: `pytest -m unit`.
- Integration tests: `pytest -m integration` and may require FFmpeg.
- Determinism tests must use explicit seeds for generated inputs and compare outputs bit-for-bit only when the contract is bit-identical.
- Numerical geometry assertions should use `np.testing.assert_allclose`/pytest.approx with justified tolerances.
- Every new rendering/math module should have deterministic, boundary, invalid-input, and important numerical/geometry coverage.
- Include ownership/aliasing tests whenever a public API exposes array-backed data.

## Verification

- Lint: `ruff check .`
- Unit: `pytest -q -m "unit and not integration and not slow"`
- Full: `pytest -q`
- Determinism: `pytest -q tests/test_determinism.py --tb=short`

## Workflow Discipline

- Use Plan Mode before multi-file edits.
- Keep tasks narrow and scoped to named files.
- Do not silently mix unrelated architectural phases.
- Inspect existing contracts before creating a new abstraction.
- Perform adversarial review before merge.
- Never use destructive Git commands or force-push as part of normal workflow.
- When the repository state differs from the documented plan, reconcile the documentation rather than guessing.

## Current Focus

Phase 4 contract-driven rendering is in progress. RenderBuffer and the compositor boundary are established; the next architectural boundary is the Render Graph. Preserve the existing PBR/multi-light implementation and integrate it through explicit render-stage contracts.
