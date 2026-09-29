# Phase 5.1 — Immutable Project State Contract

## Objective

Establish the smallest durable project-state boundary required by Track D:

`immutable state → command → new state`

Phase 5.1 defines the state snapshot only. Command execution, undo/redo, revision history, and graph traversal are deferred to Phase 5.2+.

## Contract

`ProjectState` is an immutable snapshot containing:

- explicit `project_id`;
- non-negative `revision`;
- versioned `DesignSpec` intent;
- versioned `ProcessingSettings` output policy;
- JSON-compatible project metadata.

The snapshot owns its serialized representation. Caller-owned dictionaries/models must not remain as mutable aliases into the snapshot.

## Immutability

- The snapshot itself is frozen.
- Canonical state is stored as deterministic JSON, not caller-owned mutable containers.
- `design`, `processing`, and `metadata` accessors return detached values; mutating an accessor result cannot mutate the snapshot.
- Replacing snapshot fields is rejected.
- No hidden mutable state, global project state, or implicit current revision exists.

## Determinism

Equivalent inputs produce identical canonical JSON bytes when serialized with the same schema versions.

Canonical JSON uses sorted object keys, compact separators, and UTF-8 encoding.

## Validation

- `project_id` must be a UUID.
- `revision` must be an integer >= 0; booleans are rejected.
- `DesignSpec` and `ProcessingSettings` must be their canonical validated domain types.
- Metadata must be JSON-compatible.
- Invalid state is rejected before construction.

## Compatibility boundary

Existing `DesignSpec` and `ProcessingSettings` remain separate versioned contracts. Phase 5.1 does not reinterpret their schema versions or alter persistence records.

## Non-goals

- command model;
- undo/redo;
- revision graph;
- persistence migration;
- presets;
- batch variants;
- capability compatibility;
- UI state;
- AI provider state.

## Verification

Contract → tests → implementation → Ruff → unit/integration/determinism/load/security → adversarial review → merge.
