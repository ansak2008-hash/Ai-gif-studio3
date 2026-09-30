# ResourceManager Hardening Contract

## Scope
Harden the existing process-local ResourceManager admission controller without replacing or duplicating it.

## Contract
1. Admission is atomic: under concurrent reserve calls, accepted reservations must never make reserved_bytes exceed memory_limit_bytes.
2. A request whose memory_bytes is exactly equal to the remaining budget is admitted.
3. A request whose memory_bytes exceeds the remaining budget by one byte is rejected without changing accounting.
4. A request larger than the configured limit is rejected before execution and without changing accounting.
5. ResourceRequest and ResourceManager constructor inputs reject bool and non-integer resource sizes/limits.
6. Reservation IDs are unique for the lifetime of a manager and allocation is monotonic.
7. release() is idempotent for the exact reservation object: repeated release must not change accounting below zero.
8. A reservation belonging to another manager is rejected without changing either manager's accounting.
9. A forged reservation object, even if it copies an active reservation's public fields, must not release the active reservation.
10. release() must not trust only reservation_id; ownership and reservation identity must both be established.
11. Estimation is deterministic for identical validated inputs and uses integer arithmetic for byte counts.
12. The compositor must reserve the complete estimated working set before allocating the first output RenderBuffer, and must release in a finally path after success or failure.
13. ResourceManager does not allocate render memory itself; it is an admission/accounting boundary.
14. No new registry, plugin, framework, or parallel resource abstraction is introduced.

## Non-goals
- No GPU manager redesign.
- No rendering formula changes.
- No RenderBuffer/RenderMask ownership changes.
- No change to public compositor operation names.

## Gates
Contract -> adversarial tests -> minimal implementation -> integration -> unit/integration/load/determinism/security/Ruff -> CodeQL -> adversarial review -> merge.
