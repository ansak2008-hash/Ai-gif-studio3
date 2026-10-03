# A1 + A2 Durable Recovery and Delivery Idempotency

## A1 — Durable Job Recovery

The job state machine uses a two-phase recovery cycle:

1. PROCESSING with an expired lease is atomically changed to QUEUED.
2. Stale QUEUED jobs are selected deterministically by (updated_at ASC, job_id ASC) after a 10-second grace period.
3. Each selected job is redispatched with the stable ARQ job id process_job:<job_id>.
4. A dispatch failure is contained as a transport failure. The durable job remains QUEUED and is eligible for the next scan.
5. Execution remains protected by the existing claim_for_processing() CAS, so a duplicate dispatch trigger is not duplicate execution.
6. Recovery is scheduled every 30 seconds by an ARQ cron job and additionally protected by a Redis lease with a unique ownership token. Release is conditional on that token.
7. Recovery never converts a dispatch transport failure into FAILED.

The recovery scheduler is liveness infrastructure, not a database-only invariant. Repeated scans are the mechanism that closes the liveness loop.

## A2 — At-most-once automatic delivery

Delivery identity is:

(job_id, artifact_id, channel)

The database enforces uniqueness for that identity.

State transitions:

NONE -> INTENT -> SENT

INTENT -> FAILED -> INTENT while attempts remain.

FAILED -> TERMINAL when the retry budget is exhausted.

INTENT -> UNKNOWN when an existing intent is observed after a crash window.

SENT, UNKNOWN, and TERMINAL are terminal for automatic processing.

### Crash-window policy

If Telegram may have accepted a send but the process crashes before SENT is durably recorded, the next attempt observes INTENT and moves it to UNKNOWN. It does not resend automatically.

An ambiguous exception from Telegram delivery is also recorded as UNKNOWN, not FAILED. FAILED is reserved for a confirmed-not-delivered outcome; otherwise bounded automatic retry could create a duplicate.

This intentionally chooses at-most-once automatic delivery over at-least-once delivery. A single delivery may be lost in the ambiguous crash window; a duplicate automatic Telegram delivery is not produced by recovery.

### Bounded retry

Default max_attempts = 3.

FAILED with attempt < max_attempts may retry.

FAILED with attempt >= max_attempts becomes TERMINAL and is not automatically resent.

### Atomicity requirement

begin_delivery() is an atomic get-or-create operation backed by UNIQUE(job_id, artifact_id, channel). A concurrent conflict returns the existing durable record rather than creating a second intent.

The external Telegram side effect remains outside the database transaction; therefore exactly-once delivery is not claimed.
