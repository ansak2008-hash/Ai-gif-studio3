# Phase 5.4 — Persistence Boundary

## Objective

Add a persistence boundary above the stable Phase 5.3 revision graph without allowing domain code to perform filesystem, database, or transport I/O.

## Architecture

ProjectState -> Command -> Revision -> RevisionGraph -> Persistence Contract -> Canonical Storage

The persistence contract owns representation and storage orchestration. The domain remains responsible for validating immutable revisions.

## Canonical document

A persisted revision graph is one normalized JSON document with exactly these top-level fields:

- schema_version: integer, currently 1;
- root_revision_id: lowercase SHA-256 revision id;
- current_revision_id: lowercase SHA-256 revision id;
- revisions: non-empty array of canonical Revision JSON objects.

The revisions array is ordered lexicographically by revision_id. Each revision object is validated through Revision.from_canonical_json().

The document is UTF-8 JSON, compact, sorted-key, ensure_ascii=False, allow_nan=False, and must round-trip byte-for-byte through the canonical encoder.

## Integrity invariants

- schema_version is exactly 1.
- root_revision_id and current_revision_id exist in revisions.
- exactly one revision has parent_id == null, and it equals root_revision_id.
- every non-root parent_id references an included revision.
- revision IDs are unique.
- the graph validates after reconstruction.
- current_revision_id is an existing revision.
- duplicate JSON object keys are rejected.
- NaN and Infinity are rejected.
- malformed, non-canonical, oversized, or structurally inconsistent documents are rejected.
- no filesystem/database access occurs in the domain serializer.

## Resource bounds

The boundary enforces explicit finite limits for persisted document bytes and revision count. Limits are configurable by the caller and overflow is rejected before unbounded reconstruction.

## Storage adapter

A future persistence adapter may expose write(canonical_document) and read(). Concrete filesystem/database adapters are deferred to later work. The domain must not import or call filesystem/database APIs.

## Non-goals

- crash recovery and atomic replacement (Phase 5.5);
- database schema/migrations;
- filesystem implementation;
- encryption;
- compression;
- remote storage;
- merge revisions;
- UI/timeline persistence.

## Gate

Phase 5.4 is not complete until contract tests, implementation, adversarial tests, static analysis, and CI are green.
