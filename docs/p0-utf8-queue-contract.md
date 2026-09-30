# P0 Hardening Contract — UTF-8 and Atomic Job Queue

Status: active hardening contract.

## UTF-8 canonical boundary

- Canonical string data must contain no UTF-16 surrogate code points.
- Every string must encode with strict UTF-8 before canonical persistence.
- Mapping keys must be strings and are validated with their values.
- Nested JSON-compatible mappings/sequences are bounded to a deterministic validation depth.
- Unsupported runtime objects and binary values are rejected.
- Validation is non-mutating.
- ProjectState, Revision metadata, DesignSpec payloads, and persisted project documents use the same validator boundary.
- Existing public error-type contracts are preserved at ProjectState/Revision boundaries.

## Atomic job queue

- Queue state is persisted; no process-local queue state is authoritative.
- CREATED -> QUEUED is the only enqueue transition.
- Duplicate enqueue never performs QUEUED -> CREATED.
- ARQ receives a deterministic _job_id derived from the durable job UUID, so concurrent enqueue attempts are idempotent at the transport boundary.
- QUEUED -> PROCESSING is a compare-and-set claim.
- Exactly one concurrent worker may win the claim; losers return without rendering.
- Completion/failure transitions require PROCESSING as the expected state.
- A lost claim is fail-closed: no download/render/delivery work starts.
- Retry handling may requeue a processing job only through the existing explicit retry path; it does not weaken the claim invariant.

## Gates

Contract -> tests -> implementation -> CI/CodeQL -> adversarial review -> merge.

The integration audit is executed by CI and checks the canonical and worker boundaries explicitly.
