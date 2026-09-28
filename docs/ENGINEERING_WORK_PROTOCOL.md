# Engineering Work Protocol

This document is the mandatory execution protocol for architectural work in AI GIF Studio.

## Objective

Build a deterministic, production-grade rendering and transformation engine that can scale toward desktop, Web, Android, iOS, Telegram, and future professional-editor workflows without repeated rewrites.

The long-term standard is architectural fitness, not merely green CI.

## Mandatory Phase Sequence

Every substantial phase follows this order:

1. **Contract** — define the public interface, invariants, ownership, data representation, failure behavior, and compatibility boundary.
2. **Tests** — write deterministic tests for normal cases, boundaries, invalid inputs, failure modes, and important numerical/visual invariants. Tests should fail before implementation when practical.
3. **Implementation** — implement the smallest generic abstraction that satisfies the contract. Avoid duplicated one-off fixes.
4. **CI** — run lint, unit, integration, determinism, load, and security checks that apply to the phase. Never claim a check passed unless its result was actually observed.
5. **Adversarial Review** — actively attack the design: malformed inputs, NaN/Inf, precision loss, aliasing/mutation, empty collections, shape mismatches, ordering errors, resource limits, high load, compatibility regressions, and future extension pressure.
6. **Merge** — merge only after the contract, tests, CI evidence, and adversarial review are satisfactory.
7. **Next Phase** — record the resulting architectural boundary and start the next phase with a new contract. Do not silently mix phases.

## Core Rules

- **No Code Without Contract.** Do not begin implementation when the required contract is still ambiguous.
- **Test First.** Tests are executable contract evidence, not decoration.
- **Abstraction Before Repetition.** Prefer reusable interfaces and generic components over repeated special cases.
- **Why Before How.** Before implementing a major design, identify the architectural reason, alternatives, trade-offs, and future complexity it prevents.
- **Correctness vs Architectural Fitness.** Passing tests proves tested behavior; it does not by itself prove that the design is extensible, isolated, efficient, or maintainable.
- **Determinism.** Rendering behavior must remain deterministic unless nondeterminism is explicitly part of a documented contract.
- **Ownership and Mutation.** Public APIs must make data ownership, mutability, aliasing, and copy behavior explicit.
- **Numerical Integrity.** Do not clamp, quantize, normalize, or weaken tolerances merely to make tests pass. Preserve HDR/linear-light semantics where the contract requires them.
- **Compatibility.** Preserve established contracts and legacy boundaries unless an explicit migration phase replaces them.
- **Dependencies.** Do not introduce runtime dependencies without explicit architectural justification.
- **No Silent Scope Creep.** A phase may consume existing capabilities, but it must not rewrite unrelated subsystems without a new contract.

## Rendering Architecture Direction

The canonical rendering path is being hardened around explicit contracts:

**Scene/Input → RenderBuffer → Compositor → Render Graph → PBR/Lighting → Masks/Effects → Color Management → Export**

Existing PBR and multi-light capabilities should be orchestrated through the render graph rather than unnecessarily rewritten.

Canonical internal render data should remain explicit about:
- color space / linear-light representation,
- alpha semantics,
- precision,
- dimensions and shape,
- ownership and mutability,
- deterministic ordering.

Do not silently change straight-alpha vs premultiplied-alpha semantics. Any transition must be an explicit contract.

## Review Gate

Before declaring a phase complete, answer:

- What is the contract?
- Which tests prove it?
- Which invalid inputs were attacked?
- What happens under empty, malformed, extreme, or high-load inputs?
- Are inputs mutated or aliased unexpectedly?
- Is precision preserved?
- Does the design support the next analogous feature without duplication?
- Does it preserve existing compatibility boundaries?
- What architectural debt, if any, remains intentionally documented?

If any answer is unclear, the phase is not architecturally complete even if CI is green.

## Autonomous Execution

When working through GitHub:
- inspect the current branch/base and existing architecture before editing;
- keep each phase isolated in a dedicated branch/PR;
- use tests and CI as evidence;
- perform an adversarial review before merge;
- document non-blocking risks rather than hiding them;
- after merge, verify the resulting base before starting the next phase.

This protocol is the default unless a newer repository-level engineering decision explicitly supersedes it.
