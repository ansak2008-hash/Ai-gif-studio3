# Phase 6.1 Adversarial Engineering Audit — 2026-09-30

## Scope

Red-team review of the project/editor foundation and the surrounding Telegram/API/media execution boundaries at the Phase 6.1 lineage.

CI is treated as one gate, not as proof of security or production readiness.

## Findings fixed in the hardening branch

1. Nested DesignSpec values used in FFmpeg filter construction were not all constrained to safe color, enumeration, and numeric domains.
2. The API request limit relied on Content-Length, which is optional for streamed/chunked requests.
3. Production media preflight did not consistently enforce configured input byte, dimension, and duration limits at the renderer boundary.
4. The configured GIF output byte ceiling was not enforced as a model invariant.
5. Invalid UTF-8 surrogate data could escape some canonical JSON byte-boundary paths.
6. FFmpeg inherited uppercase and lowercase proxy environment variables.
7. FFprobe probing did not bound stream count or decoded pixel count.
8. The legacy design renderer embedded user text directly in an FFmpeg filtergraph.
9. Duplicate ARQ enqueue handling could regress an already-queued job back to created.
10. A concurrent worker losing the queued-to-processing claim could continue rendering instead of failing closed.

## Findings requiring the next contract, not an ad-hoc patch

### A. ProjectEditor concurrency
ProjectEditor.execute is a multi-step read/apply/add/checkout sequence. It is not a complete concurrency transaction. Phase 6.2 must define editor ownership, serialization, isolation, cancellation, and deterministic conflict behavior.

### B. Queue-depth admission
The current application-level queue-depth check is not a cross-worker atomic admission primitive. Phase 6.2 should move admission to an atomic shared coordination boundary.

### C. ResourceManager integration
The ResourceManager contract is hardened and tested, but the production render path is not yet universally wired through it. This must be completed before claiming deterministic resource admission under concurrent rendering.

### D. API authorization model
The HTTP API currently has service-level API-key authentication rather than per-user/job authorization. If exposed to mutually untrusted clients, horizontal access control is insufficient. The deployment boundary must either remain private/internal or gain explicit principal-to-job authorization.

### E. Worker duplication
worker.py and infrastructure/worker.py represent overlapping execution paths. They currently receive hardening changes separately, but the architecture should converge them to one authoritative execution path to prevent semantic drift.

### F. Direct LayerStack persistence bounds
ProjectState persistence already imposes bounded canonical JSON. The lower-level LayerStack persistence boundary should receive equivalent byte/depth limits before it becomes a directly exposed external contract.

## Non-findings / intentionally deferred

- No registry/plugin framework is required for these fixes.
- No speculative AI provider was introduced.
- No correct API was changed to satisfy an incorrect test.
- The completed mask lifecycle contracts were not reopened.

## Gate rule

A finding is closed only after the exact latest commit passes the applicable unit, integration, load, determinism, Ruff, security, and CodeQL gates and receives an adversarial re-check.
