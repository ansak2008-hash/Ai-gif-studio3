# Phase 6.4 — Deterministic Workflow / Replay Contract

## Goal

Define an immutable, canonical workflow sequence that can be validated, serialized, reconstructed, and replayed through the existing ProjectEditor boundary without introducing a global registry, plugin framework, scheduler, persistence schema change, or hidden command discovery.

## Contract

1. **Workflow identity**
   - A workflow has a stable non-empty identifier and a positive contract version.
   - Workflow objects and operation sequences are immutable after construction.
   - Operation order is authoritative and preserved exactly.

2. **Operation descriptor**
   - Each operation declares a stable capability identifier, positive capability contract version, canonical JSON-compatible payload, and canonical JSON-compatible metadata.
   - Operation descriptors are declarative data. They do not execute commands and do not contain executable code, import paths, shell commands, or provider instructions.
   - Empty or whitespace-only identifiers are rejected.

3. **Canonical representation**
   - Workflow serialization is UTF-8 JSON using sorted object keys, compact separators, no NaN/Infinity, and deterministic ordering.
   - Re-encoding a decoded workflow MUST produce byte-for-byte identical canonical JSON.
   - Duplicate JSON object keys are rejected.
   - Unknown top-level fields are rejected.
   - The canonical representation contains workflow identity, contract version, and the ordered operation sequence.
   - Payload and metadata are copied into immutable canonical structures; caller mutation after construction cannot change the workflow.

4. **Replay boundary**
   - Replay is explicitly invoked against an existing ProjectEditor.
   - Operation descriptors are resolved by a caller-supplied resolver for each operation.
   - The resolver is local to the replay call; no process-global registry or import-time discovery is introduced.
   - The resolver MUST return a ProjectCommand compatible with ProjectEditor.
   - Capability/version validation remains explicit; replay MUST NOT silently downgrade or coerce versions.

5. **Replay determinism**
   - Given the same initial editor state, the same canonical workflow, and a deterministic resolver, replay MUST produce the same canonical final editor state and the same ordered committed operation sequence.
   - Replay order is exactly workflow order.
   - The workflow itself does not claim an operation is deterministic; deterministic behavior remains an operation/capability contract concern.

6. **Failure containment**
   - A failed operation MUST NOT create a revision for that operation.
   - The replay result reports the failing zero-based operation index and preserves the committed prefix.
   - Earlier successful operations remain committed; later operations are not attempted.
   - Resolver failures and command failures are surfaced as typed replay errors with the original exception chained.
   - Replay MUST NOT swallow arbitrary programming errors or mutate the workflow.

7. **Revision/editor integration**
   - Replay executes only through ProjectEditor.execute.
   - Existing revision identity, branching, persistence, and concurrency semantics remain unchanged.
   - Workflow descriptors are not stored in ProjectState or RevisionGraph.
   - Replay does not bypass ProjectExecutionCoordinator when the caller chooses to use it; this phase does not redesign execution concurrency.

8. **Resource and ownership boundaries**
   - Workflow objects own no resource tokens, file handles, workers, locks, or editor ownership.
   - Replay does not perform implicit resource admission or release.
   - No destructor-based or exception-swallowing cleanup mechanism is introduced.

9. **Version compatibility**
   - Workflow contract version and each operation capability version are positive integers.
   - Decoding rejects unsupported workflow schema versions.
   - Replay resolver must explicitly reject incompatible capability versions.
   - No implicit fallback, coercion, or silent downgrade is allowed.

10. **Security**
    - Payload and metadata are data only.
    - Strings in workflow JSON MUST NOT be interpreted as shell commands, module paths, URLs to download, or executable provider instructions by this contract.
    - JSON parsing rejects non-finite numbers and duplicate keys.

## Required adversarial tests

- empty identifiers are rejected;
- zero/negative/bool versions are rejected;
- workflow and operation sequences are immutable;
- nested payload/metadata mutation cannot change a workflow;
- operation order is preserved;
- canonical encoding is deterministic;
- duplicate JSON keys are rejected;
- unknown top-level fields are rejected;
- non-finite JSON numbers are rejected;
- decoded canonical JSON re-encodes identically;
- resolver is called in workflow order;
- replay commits exactly one revision per successful operation;
- replay equivalence holds for the same deterministic resolver and initial state;
- a failed operation creates no revision for that operation;
- failure reports the exact operation index and preserves the committed prefix;
- later operations are not attempted after failure;
- resolver failures are contained and chained;
- replay does not mutate workflow descriptors;
- executable-looking strings remain inert data.

## Non-goals

- no global workflow registry;
- no plugin framework;
- no command serialization registry;
- no dynamic import or provider discovery;
- no scheduler or new concurrency model;
- no ProjectState or RevisionGraph schema changes;
- no replacement of ProjectEditor;
- no automatic rollback of already committed workflow operations;
- no resource manager redesign;
- no rendering algorithm changes.

## Gates

Contract -> adversarial tests -> minimal implementation -> local verification -> CI -> CodeQL -> adversarial engineering review -> architecture review -> merge -> post-merge verification.
