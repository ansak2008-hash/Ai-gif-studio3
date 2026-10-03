# Changelog

## phase-6.5.1-closed — 2026-10-03

### Output Artifact Contract & fault containment

- Closed PR #115 with the canonical 320x320 / 6.0s / 2,400,000-byte / 256-color / 30→27→24→20→18→15 FPS output contract.
- Added artifact-level GIF analysis coverage and preserved explicit non-ladder FPS inputs.
- Hardened probe-error classification so expected probe failures are contained while unexpected programming and environment errors propagate.
- Added CI enforcement for exception-containment boundaries and verified CI + CodeQL on the reviewed head commit.


## v0.3.0-pbr-stable — 2026-09-28

### Phase 3 — PBR Scene Lighting & Multi-Light Support

- Added explicit immutable `PBRMaterial` and `DirectLight` contracts.
- Added deterministic ordered multi-light accumulation.
- Wired material and light contracts through the manuscript → depth-field → camera → PBR → color → GIF pipeline.
- Preserved legacy single-light behavior when the new scene contracts are omitted.
- Hardened PBR validation, float64 precision boundaries, GGX normalization, and Cook-Torrance grazing-denominator handling.
- Added deterministic, hardening, and end-to-end pipeline coverage.
- Verified Ruff, unit, integration, determinism, load, and CodeQL gates on the merged release commit.

