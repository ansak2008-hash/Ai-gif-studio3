# Engineering Failure Prevention Rules

## Purpose

This document records failure modes encountered during Ai GIF Studio development, the root causes, the correct repairs, and mandatory rules that prevent recurrence.

These rules are normative. Future implementation, review, CI, and merge decisions MUST follow them.

## 1. Non-Negotiable Development Gates

Every feature MUST follow this order:

1. Contract
2. Adversarial tests
3. Minimal implementation
4. Local verification
5. CI
6. CodeQL/security checks
7. Adversarial engineering review
8. Architecture/compatibility review
9. Merge
10. Post-merge verification

A green test result alone MUST NOT be treated as architectural acceptance.

A change MUST NOT be merged because it "looks correct", because a previous run was green, or because a failing test can be weakened.

The correct objective is root-cause correctness, not green CI at any cost.

## 2. No Code Without Contract

Before implementation, define:

- public interface;
- input and output domains;
- ownership and mutability rules;
- error semantics;
- version compatibility;
- determinism requirements;
- resource boundaries;
- security boundaries;
- persistence impact;
- concurrency impact;
- explicit non-goals;
- adversarial test cases.

Tests MUST be derived from the contract.

Implementation MUST NOT redefine the contract merely to satisfy an incorrect test.

## 3. Inspect the Actual Repository State First

Never diagnose from memory, a previous message, an expected diff, or an assumed branch state.

Before editing:

1. identify the exact branch;
2. identify the exact commit;
3. fetch the actual file;
4. inspect the actual surrounding code;
5. inspect the failing CI log;
6. reproduce the failure where possible;
7. identify the first/root failure.

After editing, fetch the changed file again and verify the exact bytes/content that CI will execute.

This rule exists because a previous workflow replay repair appeared correct conceptually while the committed Python source still contained over-escaped text and continued to fail collection.

## 4. Python Source Must Be Valid Before Test Execution

A syntax error is a source failure, not a test failure.

For every Python source change, verify:

```bash
python -m compileall src tests
```

before interpreting pytest failures.

If test collection fails with `SyntaxError`, `IndentationError`, or malformed source:

- fix the source first;
- do not modify assertions;
- do not delete the test;
- do not skip the test;
- do not weaken linting.

### Escaping rule

Python source escaping MUST be checked at the source-code level, not only at the intended runtime-string level.

For example, this is valid:

```python
{"value": "python -c \"raise RuntimeError()\""}
```

The source MUST NOT contain accidental doubled escaping such as:

```python
{"value": "python -c \\"raise RuntimeError()\\""}
```

when the intended Python source requires only \\".

After an escaping repair, inspect the committed file itself and run compilation.

## 5. Ruff Is a Gate, Not an Obstacle

Ruff failures MUST be fixed in source.

Never:

- disable a rule;
- add a broad noqa;
- change CI to ignore the file;
- weaken formatting requirements;
- alter tests solely to satisfy linting.

Known recurring failure modes included:

- I001 import ordering;
- UP035 import modernization;
- W292 missing final newline;
- formatting caused by unnecessary blank lines around module-level declarations.

The repository's Ruff configuration is authoritative.

After every source edit:

```bash
ruff check .
```

must pass before declaring local verification complete.

## 6. Tests Must Test the Contract, Not a Convenient Implementation

A test that fails because the implementation violates the contract MUST cause an implementation repair.

A test that is itself wrong MUST be corrected explicitly and documented.

Never make the API less correct merely to satisfy a bad test.

Required review question:

> Is the test exposing a real contract violation, or is the test assuming behavior that the contract does not require?

## 7. Compatibility Is an Explicit Gate

Backward compatibility MUST be reviewed even when all new tests pass.

### Failure: capability catalog regression

During Phase 6.3, replacing the capability catalog accidentally removed legacy entries used by existing API code.

Correct repair:

- restore all legacy catalog entries;
- preserve existing `items()` behavior;
- add regression coverage;
- do not introduce an unnecessary registry abstraction.

Mandatory rule:

> When extending an existing collection/API, preserve all existing externally used members unless an intentional breaking change is explicitly contracted.

### Failure: positional constructor regression

The new `Capability` fields were initially inserted before legacy positional fields.

Old code using:

```python
Capability(id, state, requirements, description)
```

could silently bind arguments to different fields.

This was worse than a loud failure because it could appear valid while changing semantics.

Correct repair:

- restore legacy positional ordering;
- append new fields after legacy positional fields;
- add an explicit positional compatibility regression test.

Mandatory rule:

> Adding dataclass fields MUST NOT silently change the meaning of existing positional construction.

For public constructors, review:

- positional arguments;
- keyword arguments;
- defaults;
- field order;
- return types;
- exception behavior;
- serialized representation.

## 8. Immutability Means Ownership, Not Just `frozen=True`

A frozen dataclass does not automatically make nested dictionaries/lists immutable.

For any ownership-sensitive object:

- copy caller-owned mutable inputs;
- prevent internal mutable state from escaping;
- verify nested mutation isolation;
- distinguish immutable public identity from mutable working copies;
- use explicit ownership tokens where ownership matters.

Tests MUST mutate both:

1. the original input after construction;
2. a returned nested value after construction.

The object's state MUST remain unchanged.

## 9. RenderBuffer Ownership Must Be Enforced at the Boundary

A read-only view is not sufficient if the underlying storage can still be mutated through another alias.

For owned render memory:

- define the owner;
- define every writable alias;
- prevent writable views from escaping;
- verify NumPy writeability flags and actual ownership;
- test mutation through every exposed access path;
- do not rely solely on `WRITEABLE=False`.

A failed ownership-hardening attempt MUST trigger review of the ownership model itself, not merely another flag change.

## 10. Resource Management Must Be Deterministic

Resource admission MUST NOT depend on:

- garbage collection timing;
- `del`;
- destructor side effects;
- arbitrary fixed RAM percentages;
- "approximately enough memory" heuristics.

Resource lifecycle MUST be:

```
admit -> reserve -> use -> release
```

with release in `finally`.

Every ownership token MUST have:

- explicit owner identity;
- deterministic release;
- idempotent release where required;
- rejection of release by the wrong owner;
- cleanup that cannot hide the primary failure.

Do not introduce blanket `except Exception` cleanup that destroys the original error.

## 11. Concurrency Must Define Submission Order Explicitly

An `async def` function does not establish submission order merely because callers invoke it in source order.

If ordering is part of the contract:

- allocate sequence identity synchronously at the submission boundary;
- enqueue before the first await;
- preserve per-editor FIFO;
- separate independent editor queues;
- define cancellation before mutation;
- define cancellation after commit;
- define failure and ownership semantics.

This rule came from the execution concurrency failure where sequencing was assigned only when the coroutine was awaited/scheduled, allowing reverse-await behavior to violate submission order.

Tests MUST include:

- reverse await order;
- many concurrent submissions;
- cancellation before mutation;
- cancellation after commit;
- failure after prior commits;
- independent editor isolation.

## 12. Persistence Loading Must Respect Graph Dependencies

Revision graphs cannot be reconstructed by sorting IDs alone.

A persisted child may have a smaller/larger identifier than its parent.

Correct reconstruction MUST:

- load only revisions whose parent is already available;
- preserve deterministic ordering among currently resolvable revisions;
- detect an unreachable/stuck persisted graph;
- raise a typed validation error rather than silently constructing an invalid graph.

Mandatory rule:

> Graph reconstruction MUST follow dependency topology, not identifier ordering.

## 13. Workflow Replay Must Be Declarative

Workflow descriptors are data.

They MUST NOT:

- execute shell commands;
- call `eval`;
- call `exec`;
- perform dynamic imports;
- discover providers implicitly;
- treat strings as executable instructions.

Executable-looking strings MUST remain inert data.

Replay MUST use an explicit local resolver and an existing editor execution boundary.

No global registry, plugin framework, or hidden command discovery may be introduced merely to resolve workflow operations.

## 14. Canonical JSON Must Be Strict

Canonical workflow serialization MUST define:

- UTF-8;
- deterministic key ordering;
- compact separators;
- rejection of NaN/Infinity;
- duplicate-key rejection;
- supported schema version;
- rejection of unknown top-level fields;
- byte-for-byte canonical re-encoding.

Decode/re-encode MUST produce identical canonical bytes.

Never silently normalize malformed or ambiguous JSON into an accepted workflow unless the contract explicitly permits it.

## 15. Exception Handling Must Preserve the Root Cause

When wrapping an error:

```python
raise WorkflowReplayError(...) from exc
```

MUST preserve the original exception.

Do not:

- swallow exceptions;
- replace useful tracebacks with generic messages;
- use blanket catches without a contract reason;
- catch programming errors merely to make a workflow continue.

Failure containment MUST preserve the committed prefix and MUST stop later operations when the contract requires fail-stop behavior.

## 16. Atomic Revision Semantics

For a command failure:

- no failed revision may be created;
- successful earlier operations remain committed if the contract is prefix-preserving;
- the failing operation index must be exact;
- later operations must not execute.

This must be tested at the editor/revision level, not inferred from exception messages.

## 17. CI Failures Must Be Classified Before Repair

Every failure MUST first be classified as one of:

- source/syntax;
- import/collection;
- unit behavior;
- integration behavior;
- determinism;
- load/concurrency;
- security;
- lint/format;
- infrastructure;
- dependency installation;
- workflow cancellation.

Repair MUST target the classified root cause.

### FFmpeg incident

An Actions job previously showed:

```
The operation was canceled.
```

during:

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

This was correctly classified as job cancellation during package installation, not proof of an FFmpeg dependency failure.

Mandatory rule:

> Never convert an infrastructure cancellation into an application-code diagnosis without evidence.

Do not replace working dependency installation merely because one run was canceled.

## 18. GitHub Actions Runtime Warnings Must Be Resolved at the Source

A warning about deprecated Node.js runtime usage was found in Actions.

Correct repair:

- update action versions to supported versions;
- verify the resulting workflows;
- do not use insecure compatibility overrides to suppress warnings.

Mandatory rule:

> Fix action-runtime deprecations by upgrading the affected action, not by disabling the warning.

## 19. Green CI Does Not Prove Compatibility

Phase 6.3 demonstrated that all tests can pass while a compatibility regression remains.

Therefore every phase requires an explicit adversarial review after CI.

Review at minimum:

- legacy public APIs;
- constructor compatibility;
- catalog membership;
- serialization;
- ownership;
- mutation;
- determinism;
- exception semantics;
- resource lifecycle;
- concurrency;
- security;
- persistence;
- non-goals.

## 20. Do Not Add Abstractions to Hide a Failure

When a feature fails, do not immediately introduce:

- a registry;
- a plugin framework;
- a scheduler;
- a provider abstraction;
- a generic manager;
- dynamic discovery.

First identify the actual contract boundary and make the smallest correct repair.

New abstractions require their own contract and justification.

## 21. Verify the Exact Commit

A successful run on commit A does not prove commit B.

For every repair:

1. record the repair commit SHA;
2. inspect the changed file from that SHA;
3. wait for CI associated with that exact SHA;
4. inspect every required job;
5. inspect CodeQL/security;
6. only then consider the repair verified.

If workflow runs have not appeared yet, status is **pending**, not successful.

## 22. Merge Discipline

Never merge when:

- a required check is pending;
- a required check is missing;
- only an earlier commit passed;
- a failure was hidden by rerunning without diagnosis;
- an architectural compatibility question remains unresolved;
- the actual changed source has not been inspected.

After merge:

- verify main CI;
- verify CodeQL;
- verify the merge commit;
- inspect the final branch state.

## 23. Avoid Editing Files Through Unsafe Escaping Layers

Automated file replacement can introduce escaping corruption.

When changing Python containing nested quotes, JSON, regexes, shell-looking strings, or backslashes:

1. prefer a patch/edit mechanism that preserves literal source;
2. inspect the resulting file;
3. compile it;
4. run the targeted test;
5. inspect the committed version if CI is involved.

Never assume that a string shown in a tool argument is identical to the resulting file.

## 24. Programming Language Rule

All repository programming artifacts MUST use English:

- source code;
- identifiers;
- class/function/variable names;
- enum values;
- exception names;
- comments;
- docstrings;
- test names;
- test messages;
- technical documentation;
- commit messages;
- PR technical descriptions.

User-facing Arabic/other localization belongs at the UI/localization boundary, not inside the engineering implementation.

## 25. Mandatory Root-Cause Report

Every non-trivial failure repair MUST record:

- observed symptom;
- exact failing commit;
- exact failing job;
- root cause;
- why the previous assumption was wrong;
- repair;
- regression test;
- verification evidence;
- compatibility impact;
- remaining risk.

The report MUST distinguish:

- observed fact;
- diagnosis;
- hypothesis.

A hypothesis MUST NOT be reported as a verified fact.

## 26. Phase Completion Definition

A phase is complete only when all are true:

- contract exists;
- adversarial tests exist;
- implementation is minimal and contract-compliant;
- local checks pass;
- required CI checks pass on the final commit;
- CodeQL/security passes;
- adversarial review passes;
- compatibility review passes;
- merge is complete;
- post-merge main verification passes.

"Tests pass" is not equivalent to "phase complete".

## 27. Engineering Sizing Is Based on Proof Obligations

Implementation size MUST NOT be used as a hard correctness metric.

The companion standard `docs/ENGINEERING_SIZING_AND_PROOF_OBLIGATIONS.md` is normative for deciding whether a component has sufficient engineering depth.

Future work MUST size a component from:

- contract scope;
- invariant count and criticality;
- state transitions;
- public/external boundaries;
- ownership and resource lifecycle;
- concurrency;
- serialization;
- security exposure;
- compatibility surface;
- determinism requirements;
- failure modes;
- adversarial test obligations.

LOC, test/code ratios, file counts, and class counts MAY be used only as diagnostic signals.

A component MUST NOT be expanded artificially to satisfy a numeric LOC target.

A component that appears unusually small MUST trigger a proof-obligation audit. The required response is to add missing contract coverage, tests, failure handling, or documentation only when the audit identifies a real gap.

For R2-R4 components, every applicable proof obligation MUST be explicitly covered by tests or another documented verification method before phase completion.

The governing question is:

> What must be true, how can it fail, how can we try to break it, and what evidence proves that it survives?


## Historical Failure Index

The following incidents are preserved as engineering lessons:

1. Ruff import/formatting failures -> fixed source formatting without weakening Ruff.
2. Missing final newline (W292) -> fixed file termination.
3. Database/revision-table corruption during an earlier phase -> repaired schema/source consistency before proceeding.
4. RenderBuffer ownership hardening weakness -> ownership model reviewed instead of relying on a superficial read-only flag.
5. ResourceManager lifecycle/admission concerns -> moved toward deterministic reservation/release and explicit cleanup.
6. Execution sequencing bug -> synchronous submission sequencing and per-editor FIFO.
7. Revision persistence reconstruction bug -> dependency-aware loading instead of ID-only sorting.
8. Capability catalog compatibility regression -> restored legacy entries and collection behavior.
9. Capability positional-constructor regression -> restored legacy field order and added compatibility test.
10. FFmpeg Actions cancellation -> classified as infrastructure cancellation rather than application/dependency failure.
11. GitHub Actions Node runtime warning -> upgraded action versions instead of using insecure overrides.
12. Workflow replay test SyntaxError -> corrected source escaping and verified actual committed file.
13. Workflow replay repair initially appearing fixed while committed source remained over-escaped -> introduced mandatory post-edit source inspection and compile verification.

## Final Rule

When in doubt:

**Stop. Inspect the actual source. Read the actual failure. Identify the root cause. Preserve the contract. Make the smallest correct change. Test the failure mode. Run all gates. Review compatibility. Verify the exact commit.**

Never trade correctness for a green badge.
