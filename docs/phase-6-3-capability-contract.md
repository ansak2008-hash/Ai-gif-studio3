# Phase 6.3 — Capability Contract

## Goal

Define the typed capability boundary used by editor-facing operations without introducing a process-global registry, plugin framework, dynamic provider discovery system, or speculative execution framework.

A capability describes an operation contract. It does not own project state, execute commands, allocate resources, or become a second source of truth for editor behavior.

## Contract

1. **Capability identity**
   - Every capability has a stable non-empty identifier.
   - Identifiers are immutable and unique within the capability collection owned by a caller.
   - Capability identity is data, not a Python class hierarchy or plugin entry point.
   - Duplicate identifiers are rejected deterministically.

2. **Lifecycle state**
   - A capability is explicitly one of `AVAILABLE` or `PLANNED`.
   - `PLANNED` capabilities describe future intent only and MUST NOT be executable through this contract.
   - A capability marked `AVAILABLE` must provide a complete validated input/output contract.
   - State changes are explicit data changes; capability objects are immutable.

3. **Typed domain boundary**
   - Each capability declares:
     - input domain;
     - output domain;
     - execution boundary;
     - deterministic behavior;
     - resource requirements;
     - compatibility requirements.
   - Domain identifiers are stable strings owned by the contract layer.
   - A capability cannot claim compatibility merely because two values are structurally similar.

4. **Input/output compatibility**
   - Compatibility validation is explicit and deterministic.
   - An input domain is accepted only when it is declared compatible by the capability contract.
   - Output compatibility is validated independently from input compatibility.
   - Missing, empty, or conflicting domain declarations are rejected.
   - Compatibility validation MUST NOT execute the capability or mutate project/editor state.

5. **Execution boundary**
   - Capability descriptors do not execute operations.
   - Execution remains behind the existing ProjectEditor and ProjectExecutionCoordinator boundaries.
   - A capability descriptor may identify the execution boundary, but it does not create a scheduler, registry, worker, or mutable runtime.
   - Capability validation occurs before command mutation.

6. **Determinism**
   - A capability explicitly declares whether its operation is deterministic.
   - Deterministic capabilities MUST define stable input/output semantics and be suitable for replay testing.
   - A non-deterministic capability MUST NOT be silently presented as deterministic.
   - This declaration does not replace operation-level determinism tests.

7. **Resource contract**
   - A capability declares resource requirements as metadata only.
   - Resource admission remains the responsibility of the existing ResourceManager/execution boundary.
   - Resource metadata must not become an implicit RAM heuristic or bypass explicit reservation/release.
   - No capability descriptor may own or release another subsystem's resource token.

8. **Versioning and compatibility**
   - Capability contracts carry an explicit contract version.
   - Versions are positive integers.
   - Compatibility is evaluated against the declared version and domain identifiers.
   - No implicit coercion, fallback conversion, or silent version downgrade is allowed.
   - Backward-compatible evolution requires an explicit compatibility rule or a new capability contract version.

9. **Validation and failure**
   - Construction rejects invalid identifiers, domains, versions, and contradictory state/contract combinations.
   - Validation errors are deterministic and typed.
   - Planned capabilities cannot be validated as executable capabilities.
   - Unknown compatibility requirements fail closed.
   - Capability validation must never swallow programming or contract errors.

10. **Collection semantics**
   - A caller may own a local immutable capability collection.
   - Collection construction rejects duplicate identifiers.
   - Lookup is deterministic by stable identifier.
   - No process-global mutable registry is introduced.
   - No plugin discovery or import-time registration is introduced.

11. **Project/editor integration**
   - Capability metadata is separate from ProjectState and RevisionGraph state.
   - Capability descriptors are not persisted inside project revisions unless a later contract explicitly requires versioned capability provenance.
   - Existing ProjectEditor, RevisionGraph, persistence, and execution semantics remain unchanged by this phase.

12. **Security and provenance**
   - Capability identifiers and requirements are declarative metadata, not shell commands, module paths, or executable provider instructions.
   - A requirement string MUST NOT be interpreted as an instruction to install, import, execute, or download anything.
   - External AI/provider provenance remains governed by the existing model/provider licensing gates.

## Required adversarial tests

- empty and whitespace-only identifiers are rejected;
- duplicate identifiers are rejected deterministically;
- mutable input collections cannot alter an immutable capability after construction;
- invalid or zero contract versions are rejected;
- `PLANNED` capability cannot be treated as executable;
- `AVAILABLE` capability without complete domain declarations is rejected;
- unknown input domain is rejected;
- unknown output domain is rejected;
- incompatible input domain is rejected without mutation;
- incompatible output domain is rejected without mutation;
- version mismatch fails closed;
- deterministic declaration is preserved and cannot be mutated;
- resource metadata is declarative and cannot mutate ResourceManager accounting;
- local capability collections remain isolated from each other;
- lookup is deterministic;
- duplicate registration attempts cannot replace an existing capability;
- capability validation performs no ProjectEditor mutation;
- capability metadata cannot be interpreted as executable shell/module/provider instructions;
- serialization or reconstruction, if exposed later, must preserve stable identity and contract version exactly.

## Non-goals

- no global capability registry;
- no plugin framework;
- no provider discovery;
- no command execution implementation;
- no ProjectEditor redesign;
- no timeline implementation;
- no persistence schema change;
- no rendering algorithm changes;
- no resource manager replacement;
- no automatic dependency installation or runtime loading.

## Gates

Contract -> adversarial tests -> minimal implementation -> local verification -> CI -> CodeQL -> adversarial engineering review -> architecture review -> merge -> post-merge verification.
