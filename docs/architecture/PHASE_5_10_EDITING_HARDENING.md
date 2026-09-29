# Phase 5.10 — Editing Core Hardening and Performance Safety

## Objective
Harden the existing Phase 5 editing foundations before adding more user-facing editing features. This increment closes small correctness, resource-admission, and bounded-decoding gaps without introducing a new abstraction layer.

## Verified editing capabilities
The domain editing core already contains exactly these layer-independent operations:
- crop
- scale
- translate

This phase does not rename, duplicate, or replace them.

## Contract
1. Transform commands remain immutable and deterministic.
2. A translate command must fail closed if applying its delta would place the resulting coordinate outside the existing [-320, 320] domain bounds.
3. Crop validation must use the canonical 320 canvas bound already defined by the transform contract, without a second divergent constant.
4. LayerStack canonical decoding must reject a layer array that exceeds the declared maximum before constructing LayerState objects.
5. ResourceRequest and ResourceManager constructor inputs must reject booleans and non-integer resource counts/limits; existing positive-value semantics remain unchanged.
6. Existing reservation/release semantics remain idempotent and exception-safe.
7. No rendering formulas, RenderBuffer ownership rules, blend modes, persistence schema, or public editing operation names change.
8. No registry/plugin/framework abstraction is introduced.

## Performance safety
- Reject oversized layer payloads before per-layer object construction.
- Keep resource admission arithmetic integer-bounded and deterministic.
- Avoid introducing repeated validation or allocation paths where an existing invariant can be reused.

## Non-goals
- No new transform operation.
- No new transform-to-render adapter while crop semantics remain ambiguous between project-canvas coordinates and source coordinates.
- No GPU rewrite.
- No ProjectState serialization redesign in this increment.

## Gates
Contract -> adversarial tests -> minimal implementation -> architecture/adversarial review -> unit/integration/determinism/security/Ruff -> CodeQL -> post-merge verification.
