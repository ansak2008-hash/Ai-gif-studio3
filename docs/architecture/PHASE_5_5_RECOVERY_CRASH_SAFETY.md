# Phase 5.5 — Recovery / Crash Safety

## Objective

Add crash-safe persistence orchestration above the pure Phase 5.4 persistence boundary. A process interruption must not leave the canonical persisted document partially replaced or silently corrupt.

## Architecture

RevisionGraph -> RevisionGraphPersistence.encode() -> CrashSafePersistence adapter -> canonical storage

The Phase 5.4 serializer remains pure and storage-agnostic. Phase 5.5 owns atomic replacement, recovery detection, and failure policy.

## Contract

### Canonical primary document

The primary persisted document is exactly the canonical UTF-8 document produced by `RevisionGraphPersistence.encode()`.

### Atomic replacement

A successful save must make the new canonical document visible as one complete version. The implementation must never truncate the primary file and then write the replacement in place.

The required write sequence is:

1. encode and validate the canonical document before touching storage;
2. create a temporary sibling file in the same directory;
3. write the complete UTF-8 document;
4. flush the temporary file;
5. apply filesystem durability synchronization to the temporary file;
6. atomically replace the primary path with the temporary file;
7. apply directory durability synchronization where supported/required by the adapter contract;
8. report success only after the replacement sequence completes.

The temporary file must be cleaned up on every failure path when cleanup is possible.

### Recovery

On load:

- if the primary document is valid, load it;
- if the primary document is missing but a valid recovery candidate exists, recover the candidate according to the adapter policy;
- if both primary and recovery candidate are invalid, fail closed with a typed persistence error;
- never silently accept a non-canonical document;
- never silently discard a valid primary in favor of an invalid recovery candidate.

### Integrity

Every loaded document must pass the complete Phase 5.4 decode contract before becoming application state.

A recovery candidate is not trusted merely because it exists; it must pass the same canonical decode and integrity validation.

### Failure containment

Expected storage failures must be converted into typed persistence errors with the original cause preserved.

Do not use blanket `except Exception` around the complete persistence operation. Cleanup errors must not hide the primary failure; if both occur, the primary operation failure remains the reported cause and cleanup status is retained only when the API contract exposes it.

### Ownership

The persistence adapter owns files it creates and temporary resources it allocates. It must not delete or mutate unrelated paths.

Temporary names must be derived from the target path and must not permit path traversal outside the target directory.

### Durability

The contract distinguishes:

- atomic visibility: readers see either the old complete document or the new complete document;
- file durability: the temporary file has been flushed and synchronized before replacement;
- directory-entry durability: the replacement operation is synchronized where the platform supports it.

The adapter must document platform limitations instead of claiming stronger guarantees than the operating system provides.

### Resource bounds

Phase 5.4 byte and revision limits remain mandatory. The adapter must not bypass them during recovery.

Temporary storage usage must remain bounded by the encoded document size plus a finite implementation overhead; no unbounded buffering of repeated copies is permitted.

## Adversarial requirements

Tests must cover at minimum:

- replacement failure leaves the previous primary intact;
- temporary write failure cleans up the temporary file;
- flush/sync failure does not report success;
- atomic replace failure does not report success;
- cleanup failure does not hide the primary failure;
- missing primary with valid recovery candidate;
- missing primary with invalid recovery candidate;
- valid primary wins over invalid recovery candidate;
- corrupted primary with valid recovery candidate follows explicit recovery policy;
- corrupted primary with corrupted recovery candidate fails closed;
- non-canonical recovery candidate is rejected;
- path ownership prevents traversal;
- concurrent readers never observe a partially written canonical document;
- repeated save/load remains deterministic;
- limits are enforced before reconstruction;
- no unrelated file is modified or removed.

## Storage adapter boundary

The first concrete implementation is a local filesystem adapter only. Database, remote object storage, encryption, compression, journaling, and multi-writer distributed coordination are non-goals.

The domain layer must not import filesystem APIs.

## Non-goals

- database transactions or migrations;
- remote storage;
- encryption;
- compression;
- distributed locking;
- merge revisions;
- UI recovery flows;
- automatic conflict resolution between multiple valid generations.

## Gates

1. Contract review.
2. Adversarial tests written against the contract.
3. Minimal implementation.
4. Failure-injection review.
5. Unit, integration, determinism, Ruff, security, and CodeQL.
6. Final recovery/crash-safety audit.
7. Merge only after all gates are green.
