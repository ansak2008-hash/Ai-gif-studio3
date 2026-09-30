# Adversarial Engineering Audit Disposition

## Purpose

This document records the disposition of the latest adversarial engineering and security/performance audit. The report is treated as red-team input, not as an automatically authoritative implementation plan.

## Mandatory engineering rule

New algorithmic or architectural work follows:

**Contract -> adversarial tests -> implementation -> CI/CodeQL -> performance verification -> adversarial review -> merge**

No finding is implemented solely because it sounds severe. Each finding must be verified against the actual current code and classified before changing architecture.

## Disposition

### Confirmed / immediate engineering concern

- **Frequency separation:** verify the actual implementation for linear-light residual semantics, alpha/premultiplication behavior, HDR preservation, and deterministic reconstruction. The legacy 0.5 offset must not be accepted as a contract for linear floating-point data.
- **Content-aware fill / PatchMatch:** if the implementation uses pixel-scale nested Python loops, treat this as a performance blocker. Require an explicit valid source domain disjoint from the hole, bounded memory, deterministic randomness, and boundary validation before implementation.
- **Smart selection naming:** if an implementation called GrabCut is only GMM/pixel classification, the API must not misrepresent the algorithm. Either implement a real GrabCut contract or use an accurate algorithm name.
- **LUT/HDR:** clipping HDR linear RGB to [0,1] before a LUT is forbidden when the contract promises HDR preservation. LUT domain, shaper, interpolation, and alpha invariance must be explicit.
- **Resource admission and ownership:** heavy rendering operations require deterministic resource admission/reservation and owned output buffers. Read-only flags are a defense layer, not the complete ownership contract.
- **Liquify:** inverse mapping and a unified displacement field are preferred architectural directions. Interpolation overshoot, alpha/HDR bounds, and fold/self-intersection behavior require explicit numerical contracts and adversarial tests.

### Partially valid / requires proof before implementation

- **Bit-exact determinism:** must be defined per algorithm. The contract cannot assume bitwise identity across arbitrary parallel numerical backends without specifying the execution model. Use the strongest deterministic guarantee that is technically enforceable.
- **Jacobian determinant:** a positive determinant is a useful local fold condition, but by itself is not a complete proof of global injectivity/self-intersection for every discrete warp. The actual domain, boundary conditions, and sampling model must be specified.
- **Cubic interpolation:** cubic interpolation can overshoot bounded channels, but replacing it categorically requires benchmark and quality evidence. The contract should define permitted numerical bounds and post-processing behavior.
- **scikit-learn dependency cost:** dependency weight must be measured in the actual deployment image before declaring a specific memory/size figure. Avoid speculative dependency claims.

### Unproven / reject as fact until verified

- Claims that the entire current project is inherently production-incapable.
- Claims of specific multi-hour runtimes or specific memory consumption without benchmark evidence.
- Claims that every listed algorithm must immediately be rewritten in C/Cython/Numba.
- Claims that a particular dependency consumes a fixed amount of memory without deployment measurement.

### Future design input, not current implementation scope

- Real GrabCut/Graph-Cut implementation.
- Production PatchMatch/content-aware fill.
- Multi-resolution heavy vision pipelines.
- Full HDR-aware 3D LUT/shaper architecture.
- Formal global warp-injectivity framework.

These require separate contracts, benchmarks, dependency review, memory budgets, determinism rules, and adversarial suites.

## Phase separation

This audit must not be used to reopen or destabilize completed mask/lifecycle work or to mix unrelated refactoring into Phase 5.21.

Phase 5.21 remains narrowly scoped to confirmed audit enforcement:
- SQLAlchemy declarative metadata-name compatibility.
- CI Ruff linting.
- CI formatting verification for newly added Python files without importing legacy formatting debt into the phase.

After Phase 5.21 closes, the next architectural hardening work should begin with the highest verified blocker, not with wholesale algorithm rewrites.

## Explicit non-goals

- No speculative rendering algorithm is introduced by this record.
- No new runtime dependency is justified by this record.
- No claim of production readiness is inferred from CI passing.
- No claim of production incapability is inferred from the red-team report alone.