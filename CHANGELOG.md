# Changelog

## v0.3.0-pbr-stable — 2026-09-28

### Phase 3 — PBR Scene Lighting & Multi-Light Support

- Added explicit immutable `PBRMaterial` and `DirectLight` contracts.
- Added deterministic ordered multi-light accumulation.
- Wired material and light contracts through the manuscript → depth-field → camera → PBR → color → GIF pipeline.
- Preserved legacy single-light behavior when the new scene contracts are omitted.
- Hardened PBR validation, float64 precision boundaries, GGX normalization, and Cook-Torrance grazing-denominator handling.
- Added deterministic, hardening, and end-to-end pipeline coverage.
- Verified Ruff, unit, integration, determinism, load, and CodeQL gates on the merged release commit.

