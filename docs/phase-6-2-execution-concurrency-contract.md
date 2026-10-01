# Phase 6.2 — Execution and Concurrency Contract

## Goal

Define the execution boundary around the immutable ProjectEditor so concurrent editor operations are deterministic, isolated, cancellable at explicit boundaries, and bounded by explicit admission policy without introducing a global registry, plugin framework, rendering dependency, or scheduler framework.

## Contract

1. **Synchronous submission boundary**
   - `ProjectExecutionCoordinator.submit()` is the authoritative submission boundary.
   - `submit()` is synchronous and allocates the command's monotonic sequence before any await, task scheduling, queue wait, admission wait, or editor execution.
   - Submission order is the order in which successful `submit()` calls return from the coordinator on its bound event-loop thread.
   - The coordinator is event-loop-affine. `submit()` MUST be called from the running event-loop thread associated with the coordinator.
   - The sequence is immutable and available on the returned `SubmissionHandle` immediately.

2. **Deterministic per-editor serialization**
   - Commands submitted to the same editor execute in strictly increasing submission sequence.
   - A per-editor FIFO queue is the serialization mechanism; await order, task scheduling after submission, admission completion timing, and command completion timing MUST NOT reorder commands.
   - Independent editor instances may execute concurrently.
   - A queued command cannot skip an earlier non-cancelled command for the same editor.

3. **SubmissionHandle**
   - `submit()` returns a handle immediately.
   - The handle exposes its immutable submission sequence, ownership token identity, execution state, `wait()`, and `cancel()`.
   - `await handle` is equivalent to `await handle.wait()`.
   - Cancelling a handle is cooperative and only succeeds while the command is still pending. A running or committed command is not interrupted by handle cancellation.
   - Cancelling the task that is merely waiting on a handle MUST NOT cancel the underlying submission.

4. **Atomic command boundary**
   - A command is either not started or completes as one ProjectEditor transition.
   - A command failure leaves the revision graph and current pointer unchanged.
   - Cancellation before command start prevents execution and produces no revision.
   - Cancellation is never injected into the synchronous ProjectEditor mutation itself.
   - Once ProjectEditor.execute() crosses the mutation boundary successfully, the revision remains committed even if the caller subsequently stops waiting.

5. **Admission control**
   - Admission limits are explicit configuration, not implicit memory heuristics.
   - Per-editor execution concurrency is exactly one.
   - A global admission limit, when configured, bounds concurrently admitted executions. A zero limit rejects submissions before mutation.
   - Admission rejection is represented by `AdmissionRejectedError` and never mutates editor state.
   - Admission accounting is released in a guaranteed cleanup path.
   - No fixed percentage-of-RAM threshold is used as an admission rule.

6. **Ownership and release**
   - Every admitted execution obtains an internal ownership token.
   - A token is unique to one admission and cannot be forged by copying its visible fields.
   - Release is idempotent for the same active token and cannot release another owner.
   - A cleanup/release failure after successful mutation is observable.
   - When a primary command or cancellation error already exists, cleanup failure MUST NOT replace the primary error; the cleanup failure remains observable through exception chaining.

7. **Isolation**
   - ProjectState, Revision, command metadata, and revision graph data remain immutable at the execution boundary.
   - No mutable state is shared between independent editor instances unless synchronized by the coordinator.
   - One project's cancellation, failure, or admission rejection cannot mutate or cancel another project's execution.

8. **Failure taxonomy**
   - Admission rejection, cancellation, command failure, ownership loss, and infrastructure failure remain distinguishable.
   - Programming/contract errors are not swallowed by broad exception handling.
   - Command failure is raised to the handle waiter.
   - Cleanup/release failure does not silently convert a successful command into a false success.

9. **Persistence interaction**
   - Execution serialization applies before persistence serialization for the same editor.
   - Canonical save/load remains deterministic and preserves the selected current revision.
   - No new database transaction or persistence framework is introduced by this phase.

10. **Compatibility and scope**
   - Existing ProjectEditor synchronous semantics remain unchanged.
   - The coordinator adds ordering/admission at the service boundary; it does not modify ProjectEditor invariants.
   - No registry, plugin system, scheduler framework, rendering dependency, provider integration, or process-global project state is introduced.

## Required adversarial tests

- submit #1 then #2 and await #2 before #1; execution remains #1 → #2;
- submit three commands and await them in reverse order;
- sequence is allocated and observable before the first await;
- high concurrent submission produces unique, contiguous sequences;
- pending cancellation removes a command without creating a revision;
- cancellation of a waiter does not cancel the underlying submission;
- cancellation after commit preserves the committed revision;
- command failure leaves the revision graph and current pointer unchanged;
- admission rejection leaves editor state unchanged;
- stale or forged ownership tokens cannot release another execution;
- duplicate release is harmless;
- cleanup failure does not replace a primary command failure;
- cleanup failure after success is observable;
- independent editors execute concurrently;
- queued commands on one editor remain isolated from commands on another editor.

## Non-goals

- no editor feature multiplication;
- no new command registry or plugin architecture;
- no rendering or timeline algorithm changes;
- no speculative distributed lock service;
- no process-global mutable project state;
- no implicit retry policy;
- no thread-safe cross-event-loop submission API.
