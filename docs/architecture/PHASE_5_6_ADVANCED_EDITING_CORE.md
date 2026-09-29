# Phase 5.6 — Advanced Editing Core

## Objective

Establish the next domain editing boundary above the stable command/revision/persistence core. The phase must add composable editing operations without coupling domain state to rendering, storage, Telegram, or UI concerns.

## Architecture

ProjectState -> Command -> Revision -> RevisionGraph

Phase 5.6 extends the command/domain layer only. Rendering, timeline playback, media decoding, persistence storage, and UI remain outside this contract.

## Contract-first requirements

Before implementation, define and test:

- explicit immutable editing state for the supported operation set;
- deterministic command application;
- validation before mutation;
- command metadata that is canonical and serialization-safe;
- undo/redo compatibility through the existing command/revision graph;
- no hidden global state;
- no filesystem/network access;
- ownership and mutation boundaries for edited assets;
- numerical boundary behavior for transforms and coordinates;
- deterministic identity for equivalent commands and states.

## Initial scope

The first increment should be intentionally small:

1. layer-independent transform state;
2. bounded crop/scale/translate operations;
3. explicit validation of dimensions and coordinates;
4. deterministic command application;
5. inverse/undo behavior through the existing command infrastructure;
6. adversarial tests for mutation, ownership, invalid geometry, and numerical boundaries.

Do not introduce a generic plugin/registry system.

## Non-goals

- rendering implementation;
- GPU acceleration;
- timeline/animation;
- media codecs;
- filesystem storage;
- AI generation;
- UI;
- collaborative editing;
- generic plugin architecture.

## Gates

Contract -> adversarial tests -> implementation -> architectural review -> unit/integration/determinism/security/Ruff -> CodeQL -> final audit -> merge.

Phase 5.6 is not considered complete until the editing state contract is proven immutable, deterministic, bounded, and compatible with the existing revision/command architecture.
