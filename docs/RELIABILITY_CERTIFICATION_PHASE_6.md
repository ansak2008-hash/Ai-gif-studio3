# Reliability Certification — Phase 6 Execution, Capability, and Workflow Boundaries

## Scope

This certification covers the integrated Phase 6 execution boundaries currently on `main`:

- Phase 6.2 execution concurrency;
- Phase 6.3 typed capability contract;
- Phase 6.4 deterministic workflow/replay;
- their interaction with `ProjectEditor`, revision creation, persistence, and existing compatibility surfaces.

This is a certification of the implemented boundaries and their available automated evidence. It is not a claim that the entire product is production-certified.

## Certification Basis

Certified main commit:

`4d5213e6212bed8f18a5d957123d06cc6d1017cc`

Phase 6.4 post-merge gates:

- CI #2128: success;
- CodeQL #676: success.

Phase 6.4 pre-merge gates also passed on the final PR head before merge.

## Proof-Obligation Matrix

| Boundary | Required invariant | Evidence | Status |
|---|---|---|---|
| Submission ordering | Submission sequence is allocated synchronously before any await | Execution contract tests, including reverse-await and contiguous-sequence cases | PASS |
| Per-editor ordering | One editor executes submissions in submission order | FIFO queue/drain implementation and concurrency tests | PASS |
| Cancellation | Pre-mutation cancellation does not execute; post-commit cancellation cannot erase committed state | Cancellation contract tests | PASS |
| Admission | Admission is explicit and ownership is released through deterministic paths | Ownership/admission tests and coordinator implementation | PASS |
| Ownership | Release requires the exact coordinator-owned token; duplicate release is idempotent | Ownership identity tests | PASS |
| Failure preservation | Primary execution failure is preserved when cleanup also fails | Cleanup/error-preservation tests | PASS |
| Capability identity | Capability identifiers are non-empty and stable | Capability validation tests | PASS |
| Capability typing | Input/output domains and execution boundary are explicit | Capability contract tests | PASS |
| Capability compatibility | Domain/version mismatch fails closed | Compatibility tests | PASS |
| Capability immutability | Capability and collection state cannot be mutated through the public object interface | Immutability tests | PASS |
| Legacy compatibility | Legacy catalog entries and positional constructor semantics remain available | Compatibility regression tests | PASS |
| Workflow identity | Workflow identifiers and supported schema versions are explicit | Workflow validation tests | PASS |
| Workflow immutability | Operation descriptors and nested caller-owned data cannot mutate a constructed workflow | Mutation-isolation tests | PASS |
| Canonical JSON | Deterministic key ordering, compact representation, finite numbers, duplicate-key rejection, and strict validation | Canonical encoding/decoding tests plus shared canonical validation | PASS |
| Canonical round-trip | A supported workflow decodes and re-encodes to identical canonical JSON | Round-trip test and constructor schema-version gate | PASS |
| Replay order | Resolver and execution follow workflow order | Ordered resolver/replay tests | PASS |
| Revision atomicity | A failed operation creates no revision for that operation | Command-failure and prefix-preservation tests | PASS |
| Failure containment | Failure index and committed prefix are preserved; later operations are not attempted | Replay failure tests | PASS |
| Security boundary | Executable-looking strings remain inert declarative data | Explicit inert-data regression test | PASS |
| Global-state isolation | Workflow replay uses a caller-supplied local resolver and introduces no registry/plugin discovery | Contract, implementation inspection, and repository search | PASS |
| Persistence isolation | Phase 6 workflow replay does not change ProjectState/RevisionGraph schema | Contract and diff inspection | PASS |

## Adversarial Findings Resolved During Phase 6.4

1. The workflow identifier validation message did not match the contract test. The implementation was corrected rather than weakening the test.
2. A malformed executable-looking test string caused Python syntax/collection failures. The fixture was corrected and the source was rechecked.
3. The workflow constructor initially accepted positive schema versions that the decoder could not reconstruct. Construction now rejects unsupported schema versions, and a regression test covers the boundary.
4. The final workflow replay test formatting was corrected to satisfy the repository Ruff gate.

These were root-cause fixes; no production contract was weakened to accommodate an incorrect test.

## Residual Boundaries

The following are deliberately outside this certification:

- full rendering/artifact correctness;
- RenderBuffer ownership hardening;
- ResourceManager redesign and stress certification;
- Telegram delivery/network fault certification;
- end-to-end artifact size/duration/FPS guarantees;
- external provider reliability;
- process crash recovery and disaster recovery;
- production-scale persistence corruption recovery.

These remain explicit future proof obligations and must not be inferred as certified by Phase 6.

## Architecture Assessment

No new global registry, plugin framework, scheduler, dynamic import mechanism, persistence schema, or hidden command discovery was introduced by Phase 6.4.

Workflow replay remains a declarative boundary. Execution remains mediated by the existing editor boundary, and concurrency remains an explicit service concern.

Capability resource metadata remains declarative metadata. It is not treated as a resource ownership token and does not silently replace ResourceManager semantics.

## Certification Decision

**Phase 6.2 + 6.3 + 6.4 execution/capability/workflow boundary certification: PASS.**

This decision is limited to the proof obligations listed above and the evidence identified in this document.

The next engineering priority is the broader reliability hardening track, beginning with the still-open ownership/resource/fault-containment obligations rather than adding new product abstractions.
