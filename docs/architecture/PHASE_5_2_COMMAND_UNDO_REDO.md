# Phase 5.2 — Command / Undo / Redo Contract

## Objective

Establish the deterministic transition boundary:

`ProjectState → immutable Command → ProjectState`

and a local undo/redo controller over immutable snapshots.

## Command contract

A command:
- is immutable;
- accepts exactly one `ProjectState`;
- returns a new `ProjectState`;
- never mutates the input state;
- is deterministic for identical input and command configuration;
- increments the resulting state's revision by exactly one;
- rejects incompatible state/configuration with a typed exception.

Phase 5.2 starts with explicit replacement commands for DesignSpec and ProcessingSettings. Domain-specific layer/effect commands are added only when their state mutation semantics are defined.

## Undo / Redo contract

`CommandHistory` owns mutable navigation state, not mutable project state.

- `execute(command)` applies the command to the current immutable snapshot, pushes the previous snapshot onto undo history, clears redo history, and makes the new snapshot current.
- `undo()` restores the most recent previous snapshot and moves the current snapshot to redo history.
- `redo()` restores the most recently undone snapshot and moves the current snapshot back to undo history.
- undo/redo do not mutate any stored snapshot;
- executing a new command after undo invalidates the redo branch;
- empty undo/redo operations raise a typed history exception;
- history is process-local in 5.2; persistence and revision graph semantics are deferred.

## Non-goals

- revision graph;
- persistent command log;
- database history;
- branching revisions;
- presets;
- batch variants;
- capability compatibility;
- UI bindings.

## Verification

Contract → tests → implementation → Ruff → unit/integration/determinism/load/security → adversarial review → merge.
