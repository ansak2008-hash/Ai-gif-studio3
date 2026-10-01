# Phase 6.2 — Execution and Concurrency Contract

## Goal

Define the execution boundary around the immutable ProjectEditor so concurrent editor operations are deterministic, isolated, cancellable at explicit boundaries, and bounded by admission policy without introducing a global registry, plugin framework, or rendering dependency.

## Contract

1. **Single logical owner per editor instance**
   - A ProjectEditor instance has exactly one active execution owner at a time.
   - No two commands may mutate the same editor graph concurrently.
   - Ownership is explicit at the execution boundary; callers must not coordinate by reaching into ProjectEditor internals.

2. **Deterministic per-editor serialization**
   - Commands admitted to the same editor execute in a single deterministic order.
   - The execution boundary assigns a monotonic admission sequence before execution.
   - Sequence order, not task scheduling or completion timing, determines command order.
   - Independent editor instances may execute concurrently without sharing mutable editor state.

3. **Atomic command boundary**
   - A command is either not started, or completes as one editor transition.
   - A command failure must leave the revision graph and current pointer unchanged.
   - A cancellation observed before command start prevents execution and produces no revision.
   - Cancellation is not injected into the middle of ProjectEditor graph mutation.
   - If cancellation arrives after command execution has crossed the mutation boundary, the completed command remains committed and cancellation is reported only at the next explicit cancellation boundary.

4. **Admission control**
   - Admission limits are explicit configuration, not implicit memory heuristics.
   - Per-editor concurrency is exactly one.
   - Global concurrency/admission limits, when enabled, reject or defer work deterministically according to the configured policy.
   - Rejected work must not mutate editor state and must be distinguishable from command failure.
   - No fixed percentage-of-RAM threshold is used as an admission rule.

5. **Ownership and release**
   - Every admitted execution obtains an ownership token/lease at the execution boundary.
   - The ownership token is released in a guaranteed cleanup path.
   - Release is idempotent for the same owner and must not release another owner's admission.
   - A failed release is observable and must not silently convert a successful command into a false success.

6. **Isolation**
   - ProjectState, Revision, command metadata, and revision graph data remain immutable at the execution boundary.
   - No mutable state is shared between independent editor instances unless explicitly synchronized by the execution boundary.
   - One project's cancellation, failure, or admission rejection must not corrupt or cancel another project's execution.

7. **Failure taxonomy**
   - Admission rejection, cancellation, command failure, ownership loss, and infrastructure failure remain distinguishable.
   - Programming/contract errors are not swallowed by a broad exception handler.
   - Cleanup/release errors must not mask an active primary command or cancellation error.

8. **Persistence interaction**
   - Execution serialization applies before persistence serialization; concurrent saves of the same editor are serialized through the same ownership boundary.
   - Canonical save/load remains deterministic and preserves the selected current revision.
   - No new database transaction or persistence framework is introduced by this phase.

9. **Compatibility and scope**
   - Existing ProjectEditor synchronous semantics remain valid for single-owner callers.
   - No registry, plugin system, scheduler framework, rendering dependency, or provider integration is introduced.
   - The execution boundary must remain usable by future editor tools, timeline operations, and render requests without changing ProjectEditor invariants.

## Required adversarial tests

- two concurrent commands against one editor are serialized and produce deterministic revision order;
- commands against independent editors execute concurrently without cross-talk;
- cancellation before admission creates no revision;
- cancellation after admission but before command start creates no revision;
- cancellation after the mutation boundary does not roll back a committed revision;
- command failure leaves current revision and graph unchanged;
- admission rejection leaves editor state unchanged;
- stale/wrong ownership token cannot release another execution;
- duplicate release is harmless and observable only according to the defined release contract;
- release failure does not replace an active command failure;
- high concurrency does not produce duplicate or skipped admission sequence numbers;
- canonical save/load after serialized execution preserves graph identity and current revision.

## Non-goals

- no editor feature multiplication;
- no new command registry or plugin architecture;
- no rendering or timeline algorithm changes;
- no speculative distributed lock service;
- no process-global mutable project state;
- no implicit retry policy.
