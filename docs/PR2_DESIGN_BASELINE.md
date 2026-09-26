# PR #2 — Smart Square Composition Engine

Source: `ansak2008-hash/ai-gif-studio`
Commit: `0afe56b43331217600c80c24dbcaf41e440cfeb3`

## Motivation

- Provide a renderer-neutral Composition Engine that converts arbitrary-aspect source video into a design-ready 320×320 canvas with smart cropping, preserved proportions, and clear internal foreground bounds for subsequent framing.
- Avoid naive centering or full-canvas frames by creating an editorial internal foreground with breathing room and predictable clip bounds so the Frame Engine can follow the actual design surface.

## Description

- Add dependency-free TypeScript schemas and types exposing `CompositionInput`, `CompositionLayout`, `Bounds`, `FocusPoint`, and `COMPOSITION_CANVAS_SIZE` in `src/composition/schema.ts` to define the composition/layout boundary.
- Implement `createComposition()` in `src/composition/engine.ts` with focus-preserving smart crop, uniform `mediaScale` to prevent stretching, `designRatio` heuristics for extreme aspect ratios, constrained foreground scale (70–95%), anchor-aware placement, and support for `circle`, `rounded-rect`, and `rect` clips.
- Export the composition API via `src/composition/index.ts` and `src/index.ts`, add a README describing the Frame Engine contract, and include a small test shim (`src/node-test-shim.d.ts`) and `tsconfig.json` plus `package.json` and `.gitignore` for development.
- Add unit tests in `src/composition/engine.test.ts` covering standard aspect recognition, smart crop behavior, focus retention, circular compositions, arbitrary ratios, and input validation.

## Testing

- Attempted `npm install` but it failed with a 403 from the npm registry so the local TypeScript installation was used instead (registry access issue).
- Built and ran tests with `tsc -p tsconfig.json && node --test dist/composition/engine.test.js`, and all automated tests passed (5 tests, 0 failures).
- Type-checking and test run succeeded using the system `tsc` and `node` binaries in the environment.
