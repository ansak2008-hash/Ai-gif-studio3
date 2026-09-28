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
