# PR #1 — Versioned Central Render Configuration

Source: `ansak2008-hash/ai-gif-studio`
Commit: `0ae2fa8e7b10c3c168183868f1695b197ed04ce9`

## Motivation

- Provide a single, versioned central configuration for rendering so engines read canvas size, duration, output limits, FPS, capabilities, and encoding/composition settings from one place instead of scattering magic values across the codebase.
- Make defaults configurable and future-proof (so changing 320×320 later is done in one location) while preserving backward compatibility with older flat option names.

## Description

- Add a new `src/config/index.js` module that exports `DEFAULT_RENDER_CONFIGURATION`, `RENDER_CONFIGURATION_SCHEMA`, `createRenderConfiguration`, `migrateLegacyConfiguration`, and `validateRenderConfiguration` with deep-freeze and merge helpers.
- Populate defaults requested: `canvas` 320×320, `durationSeconds` 6, `maximumOutputBytes` 2_400_000, preferred `fps` 30 with fallback ladder `[30,27,24,20,18,15]`, supported background modes, frame geometries/animation paths, foreground scale range, quality presets, palette, dithering, crop, and composition settings.
- Implement validation of individual fields and cross-field constraints (e.g., FPS ladder ordering, palette ranges, quality preset constraints, crop/composition flags) and add migration of legacy flat keys (`width`, `height`, `duration`, `maxOutputBytes`, `preferredFps`, `fpsFallbackLadder`) into the v1 nested schema.
- Add `test/config.test.js` with unit tests that verify defaults, legacy migration, and validation behavior; add minimal `package.json` with a `test` script.

## Testing

- Ran `npm test`, which executed the Node tests and passed (3 tests passed covering defaults, migration, and validation).
- Ran `git diff --check` which reported no whitespace or patch errors.
