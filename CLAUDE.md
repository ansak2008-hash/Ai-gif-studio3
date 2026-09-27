# AI GIF Studio — Claude Code Instructions

## Architecture
- `src/ai_gif_studio/temporal_engine/` contains the deterministic Video→GIF pipeline and the isolated Manuscript prototype foundation.
- Video→GIF and Manuscript Animation are separate features. NEVER mix their data flow, APIs, or rendering stages.
- Manuscript Animation currently uses `camera.py`, `manuscript_plane.py`, `bevel.py`, and `depth_field.py`.
- Do not introduce Gemini/DeepSeek runtime integrations. External engineering reports are input for human-reviewed changes only.


## Phase Status

| Phase | Status | Scope |
|---|---|---|
| 1 | Implemented | Perspective Camera + Manuscript Plane |
| 2 | Verification in progress | Canonical SDF + Bevel + Normals |
| 3 | Not started | PBR Material + Environment |
| 4 | Not started | Motion separation |
| 5 | Not started | Color / export expansion |
| 6 | Not started | Final integration |

## Batch 11 Status
- Phase 1 (Perspective Camera): implemented — `camera.py`, `manuscript_plane.py`.
- Phase 2 (Canonical Depth): implemented — `depth_field.py`, `bevel.py`.
- Phase 3 (Material/Environment): NOT STARTED as an integrated Batch 11 stage. An older/prototype `material.py` exists in `temporal_engine`; treat it as legacy until the Phase 3 architecture explicitly replaces or adopts it. Do not modify it during Phase 2 verification.
- Motion, color/export expansion, and final integration remain later phases.

## Hard Rules
1. NEVER use `from X import *`.
2. NEVER use `warpAffine` for the Manuscript camera path. Use perspective projection + homography + `warpPerspective`.
3. NEVER use Sobel(alpha) as the source of Manuscript surface normals. Use the canonical SDF/bevel field.
4. NEVER add `random`, `time.time`, or unseeded `np.random` to a render path.
5. After edits, run `ruff check .` and `pytest -q -m "unit and not integration and not slow"` when the local environment is available.
6. `cinematic_camera.py` is deprecated. Do not modify it; delete only as part of an explicit migration.
7. NEVER introduce a new runtime dependency without explicit approval.
8. Do not weaken mathematical/visual acceptance thresholds merely to make CI green.
9. Do not claim tests passed unless their output was actually observed.
10. Do not modify the Video→GIF pipeline while implementing Manuscript Animation features unless the change is explicitly required and isolated.

## File Ownership
- `temporal_engine/__init__.py`: explicit public API only; avoid broad/god exports.
- `bevel.py`: deterministic bevel profile and its closed-form derivative.
- `depth_field.py`: canonical signed distance field, height construction, and surface normals.
- `camera.py`: CameraState, CameraModel, and projection.
- `manuscript_plane.py`: ManuscriptPlane, projected corners, homography, and perspective warp.

## Test Conventions
- Unit tests: `pytest -m unit`.
- Integration tests: `pytest -m integration` and may require FFmpeg.
- Determinism tests must use explicit seeds for generated inputs and compare outputs bit-for-bit only when the contract is bit-identical.
- Numerical geometry assertions should use `np.testing.assert_allclose`/pytest.approx with justified tolerances.
- Every new rendering/math module should have deterministic, boundary, and geometry/monotonicity coverage.

## Verification
- Lint: `ruff check .`
- Unit: `pytest -q -m "unit and not integration and not slow"`
- Full: `pytest -q`
- Determinism: `pytest -q tests/test_determinism.py --tb=short`

## Workflow Discipline
- Use Plan Mode before multi-file edits.
- Use `/clear` between independent phases; use `/compact` only when continuing the same task.
- Keep tasks narrow and scoped to named files.
- Use the verifier subagent for verification and the scout subagent for read-only file inspection.
- Never use destructive Git commands or push without explicit approval.

## Current Focus
Phase 2 verification / Phase 3 preparation only. Inspect and harden the existing Camera + Depth foundation before implementing Material/Environment.
