# Fault Containment Hardening

## Contract

1. A job's primary processing exception remains the exception observed by the caller; cleanup failures must never replace or obscure it.
2. Resource cleanup is attempted for every acquired resource, even when an earlier cleanup operation fails.
3. If processing is cancelled, cancellation propagates unchanged and is never converted into a normal operational failure, retry, or success result.
4. Cancellation is not logged as an ordinary processing failure by the stage boundary.
5. Cleanup-only failure is observable: when there is no primary processing exception, the cleanup exception is raised to the caller.
6. Cleanup errors are logged with resource identity and exception type, without logging secrets or full payload contents.
7. Fault containment must not use a blanket catch-all around the processing body, and must not swallow programming/contract errors.
8. The worker's database and Telegram client are always closed after acquisition, while temporary source files are removed when present.
9. Existing successful processing behavior and return values remain unchanged.
10. No retry policy, queue ownership model, rendering algorithm, or persistence abstraction is changed by this hardening step.

## Test-first adversarial cases

- processing raises RuntimeError, Telegram cleanup also raises: original RuntimeError survives;
- processing is cancelled: CancelledError survives unchanged;
- source-file cleanup fails while database cleanup succeeds: both cleanup attempts occur and the cleanup failure is observable when no primary exception exists;
- multiple cleanup failures occur: all cleanup attempts execute, with deterministic exception selection and logging;
- normal processing: all resources close and the existing result is returned;
- no acquired resource: cleanup does not fabricate or close unowned resources.

## Non-goals

- no new retry/backoff mechanism;
- no blanket exception suppression;
- no changes to artifact identity/idempotency;
- no RenderBuffer, compositor, or rendering changes;
- no new registry/plugin abstraction.
