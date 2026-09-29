# Phase 5.3 — Revision Graph

## Contract

Phase 5.3 adds a small domain-level revision graph above the immutable ProjectState and Phase 5.2 command/history boundary.

ProjectState -> Command -> Revision -> RevisionGraph

### Revision

A Revision is immutable and content-addressed.

It contains:

- revision_id: deterministic SHA-256 identity;
- parent_id: one explicit parent, or None only for the root;
- immutable ProjectState;
- canonical command metadata.

The revision identity is derived from canonical parent identity, canonical state, and canonical command metadata. Equivalent inputs therefore reconstruct the same identity.

### RevisionGraph

RevisionGraph is the mutable index/navigation boundary; revision nodes themselves remain immutable.

It supports:

- root creation;
- adding a revision with an existing parent;
- branching by allowing multiple children of one parent;
- checkout of an existing revision;
- ancestry discovery;
- ancestor checks;
- bounded node count;
- structural/content validation.

The graph does not mutate ProjectState, execute commands, or perform persistence.

### Rejection rules

The graph rejects:

- malformed revision IDs;
- non-Revision nodes;
- non-root roots with parents;
- orphan parents;
- duplicate revisions;
- revision identity collisions;
- corrupted revision content;
- missing current nodes;
- node-count overflow.

### Serialization boundary

Revision.canonical_json and Revision.from_canonical_json() provide a deterministic domain serialization contract. Persistence is deliberately deferred to Phase 5.4.

### Concurrency

Graph mutations and reads use a small RLock around the in-memory index. This is only an in-process consistency boundary; it is not a persistence or distributed-concurrency mechanism.

## Explicit non-goals

Phase 5.3 does not add:

- filesystem/database access;
- persistence adapters;
- crash recovery;
- multi-parent/merge revisions;
- UI/timeline abstractions;
- provider/AI integration;
- new runtime dependencies.

## Adversarial gate

The Phase 5.3 suite covers:

- mutation attempts;
- invalid parents and orphan rejection;
- duplicate revisions;
- branch divergence;
- checkout;
- undo/redo state materialization;
- deterministic reconstruction;
- serialization corruption;
- deep graphs;
- bounded graph growth;
- concurrent-read simulation.

Phase 5.4 starts only after this contract and its adversarial suite are green on CI.
