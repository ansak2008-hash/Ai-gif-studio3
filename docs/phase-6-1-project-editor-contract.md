# Phase 6.1 — Project Editor Boundary Contract

## Goal

Provide one narrow application boundary that composes the existing immutable `ProjectState`, `ProjectCommand`, `Revision`, `RevisionGraph`, and `RevisionGraphPersistence` primitives without introducing a registry, plugin system, or rendering dependency.

## Contract

- `ProjectEditor.create(initial_state, *, max_revisions=10_000)` creates exactly one root revision.
- The root revision has no parent and canonical command metadata identifying the root operation.
- `current_state` and `current_revision_id` always refer to the same immutable revision.
- `execute(command, command_metadata)`:
  - accepts only a `ProjectCommand`;
  - requires JSON-compatible mapping metadata;
  - applies the command exactly once to the current state;
  - requires the command to advance the state revision by exactly one;
  - creates one content-addressed child revision;
  - moves the editor current pointer to that revision;
  - leaves prior revisions immutable.
- A failed command or invalid metadata must not add a revision or move the current pointer.
- `checkout(revision_id)` moves only the current pointer; it never mutates or deletes revisions.
- `canonical_json` delegates to the existing bounded canonical revision-graph persistence boundary.
- `from_canonical_json(document)` restores an equivalent editor with the persisted current revision selected.
- The boundary must preserve revision identity and deterministic canonical serialization.
- No filesystem, database, rendering, provider, registry, or plugin dependency is introduced.

## Required tests

1. Root creation is deterministic for equivalent state/metadata.
2. Execute creates exactly one child revision and advances state exactly once.
3. Previous state/revision remains unchanged after execution.
4. Invalid command/metadata fails closed without graph mutation.
5. Checkout restores an existing immutable revision.
6. Canonical save/load round-trip preserves the complete graph and current revision.
7. Branching from a checked-out revision preserves both branches and their identities.
8. Persistence bounds are enforced through the existing persistence contract.
