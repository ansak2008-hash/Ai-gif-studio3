# Automatic design presets

The design pipeline now exposes eight deterministic, allowlisted presets through the application API.

## Presets

- `luxury_gold` — dark luxury composition with gold typography and animated shine.
- `silver_chrome` — silver/chrome typography with animated shine.
- `arabic_calligraphy` — Arabic calligraphy using the supported Arabic font chain and fade-in.
- `3d_name` — deterministic layered 3D name treatment with slide-in.
- `royal` — gold royal frame and pulsing typography.
- `neon` — neon frame/material with bounded pulse animation.
- `minimal` — restrained flat typography and frame.
- `dark_luxury` — dark luxury background with chrome typography.

## API

- `GET /v1/presets` returns all preset names and validated DesignSpec payloads.
- `GET /v1/presets/{name}` returns one validated preset.
- `PUT /v1/jobs/{job_id}/preset/{name}` applies a preset to an existing job.

All preset composition is allowlisted and passes the same Pydantic DesignSpec validation as direct submissions.

## Animation boundary

Typography animation is deterministic FFmpeg expression-based motion: fade, slide, pulse, and shine. It is intentionally not presented as a generative AI model.

The 3D effect is layered depth in a 2D render. “4D” is treated as temporal animation rather than a physical fourth spatial dimension.

## Failure-learning gates

CI now runs:

1. Python bytecode compilation.
2. Ruff linting.
3. FFmpeg filter capability checks for `drawtext` and `drawbox`.
4. The full pytest suite.

This prevents syntax regressions and missing runtime filter capabilities from reaching merge.
