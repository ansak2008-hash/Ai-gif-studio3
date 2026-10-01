# Artifact / Render Idempotency Hardening

## Contract

1. Artifact identity is the tuple (job_id, artifact_type, storage_path).
2. Re-registering the same identity with identical bytes, size, and MIME type returns the existing artifact record and never creates a second record.
3. The idempotency guarantee holds under concurrent registrations from independent database sessions.
4. Re-registering an existing identity with different bytes or size is rejected without replacing the existing record.
5. A uniqueness constraint at the database boundary is the source of truth; application-side pre-checks alone are insufficient under races.
6. A losing concurrent registration must recover from the uniqueness conflict, re-read the committed record, validate content identity, and return that record.
7. No partial artifact record may be published when registration fails.
8. Artifact registration remains content-addressed by SHA-256 and does not depend on wall-clock timestamps, UUID generation, or dictionary ordering for identity.
9. Existing public ArtifactRepository.register() behavior is preserved for sequential callers.
10. No new registry, plugin, cache, scheduler, or rendering abstraction is introduced.

## Adversarial cases

- two independent sessions register the same artifact concurrently;
- repeated sequential registration returns one record;
- changed content at the same identity is rejected;
- database uniqueness, rather than a Python pre-check, closes the race window.

## Non-goals

- no GIF encoding algorithm changes;
- no RenderBuffer/RenderMask changes;
- no artifact retention-policy changes;
- no new render scheduler or persistence framework.
