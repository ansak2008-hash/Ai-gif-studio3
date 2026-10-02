# Engineering Sizing and Proof Obligations Standard

## Purpose

This standard defines how Ai GIF Studio decides whether a component has enough engineering depth to be trusted.

The project MUST NOT use arbitrary implementation line counts as a correctness requirement.

Lines of code, test/code ratios, and file size are diagnostic signals only. They MUST NOT be acceptance gates by themselves.

The acceptance unit is:

**contract -> invariants -> proof obligations -> adversarial tests -> implementation -> verification evidence**

## 1. Core sizing rule

A component is correctly sized when its implementation contains everything required to satisfy its contracted behavior and nothing unrelated that exists only to increase size.

Do not add code merely to reach:

- a target number of implementation lines;
- a target number of test lines;
- a target test/code ratio;
- a target number of classes;
- a target number of files.

A small implementation with complete proof obligations is preferable to a larger implementation with unverified behavior.

A component that is suspiciously small MUST be investigated, not automatically expanded.

## 2. Risk-based engineering depth

Every new or materially changed component MUST be classified by its highest applicable risk.

### R0 — Pure/local logic

Examples:

- formatting;
- simple value transformation;
- deterministic helper functions.

Required:

- explicit contract;
- valid input and output tests;
- boundary tests where meaningful.

### R1 — Domain behavior

Examples:

- state transformations;
- image/design operations;
- capability validation.

Required:

- contract;
- invariants;
- positive tests;
- invalid-input tests;
- boundary tests;
- compatibility review when an existing API is touched.

### R2 — State, persistence, or ownership

Examples:

- revision graphs;
- immutable descriptors;
- RenderBuffer;
- artifact ownership.

Required:

- all R1 obligations;
- ownership/mutation analysis;
- corruption or aliasing tests;
- failure-state tests;
- serialization tests where applicable;
- explicit recovery/failure semantics.

### R3 — Concurrency, resources, or external boundaries

Examples:

- execution coordination;
- ResourceManager;
- FFmpeg adapters;
- Telegram delivery boundaries.

Required:

- all R2 obligations;
- ordering/lifecycle model;
- cancellation tests;
- injected-failure tests;
- cleanup verification;
- exact ownership/release semantics;
- infrastructure failure classification;
- adversarial review.

### R4 — Critical system boundary

Examples:

- workflow replay;
- security-sensitive parsing;
- final artifact admission;
- persistence recovery;
- code that can corrupt durable project state.

Required:

- all R3 obligations;
- explicit threat model;
- deterministic replay or equivalent reproducibility proof where applicable;
- malformed-input matrix;
- compatibility matrix;
- fault-injection coverage;
- exact-commit CI evidence;
- independent adversarial engineering review;
- architecture review before merge.

## 3. Invariant-first sizing

Before implementation, enumerate the invariants.

Each invariant MUST have at least one direct test that fails if that invariant is broken.

Critical invariants MUST additionally have an adversarial test.

Examples:

- submission sequence is allocated before the first await;
- a failed workflow operation creates no revision;
- a committed workflow prefix remains committed;
- a released resource cannot be released by another owner;
- a workflow descriptor cannot be mutated through a returned nested object;
- canonical JSON rejects duplicate keys;
- an artifact cannot exceed its hard size limit.

If an invariant cannot be expressed as a test or observable verification, the contract MUST explain why and define an alternative proof.

## 4. Minimum test obligations

Test counts MUST be derived from contract obligations rather than arbitrary ratios.

For each public input boundary, provide where applicable:

1. valid behavior;
2. invalid behavior;
3. boundary behavior;
4. adversarial behavior.

For each state transition:

1. successful transition;
2. invalid transition;
3. failure transition;
4. cancellation transition when cancellation is supported.

For ownership-sensitive code:

1. caller mutation after construction;
2. returned-value mutation;
3. valid release;
4. duplicate release;
5. wrong-owner release where applicable.

For serialization:

1. round trip;
2. canonical representation;
3. malformed input;
4. unknown fields;
5. duplicate fields;
6. unsupported version;
7. non-finite numeric values where numbers are accepted.

For concurrency:

1. required ordering;
2. reverse scheduling/await ordering;
3. concurrent submissions;
4. cancellation before mutation;
5. cancellation after commit;
6. failure isolation.

Not every category applies to every component. The contract MUST identify non-applicable categories explicitly for R2+ components.

## 5. Adversarial test priority

For R2, R3, and R4 components, adversarial tests are mandatory.

Adversarial tests SHOULD target:

- boundary values;
- malformed structures;
- unexpected types;
- mutation attempts;
- aliasing;
- repeated calls;
- duplicate release;
- wrong ownership;
- cancellation;
- injected failures;
- partial failures;
- reordered execution;
- corrupted persistence;
- unsupported versions;
- executable-looking data;
- resource exhaustion;
- cleanup failures.

The objective is to attack assumptions, not to maximize test count.

## 6. Property-based and model-based testing

Use property-based testing when the contract describes a broad input space or algebraic property.

Good candidates include:

- canonical serialization;
- workflow generation;
- numeric boundary transformations;
- resource accounting;
- graph reconstruction.

Use model-based testing when behavior is primarily a state machine.

Good candidates include:

- execution lifecycle;
- resource admission/release;
- revision graph transitions;
- workflow replay.

These techniques are required when ordinary example-based tests cannot credibly cover the relevant state/input space, especially for R3/R4 components.

## 7. Fault injection obligations

R3 and R4 components MUST define injectable failure points where practical.

Examples:

- allocation failure;
- encoder failure;
- FFmpeg failure;
- persistence failure;
- resolver failure;
- cancellation;
- timeout;
- cleanup failure;
- disk-full simulation.

For each injected failure, verify:

- primary error is preserved;
- owned resources are released;
- no invalid state is committed;
- partial artifacts are not delivered;
- committed prefix semantics are preserved where required.

## 8. Determinism obligations

A deterministic component MUST identify its determinism level:

- D0: determinism not required;
- D1: semantic/observable result deterministic;
- D2: serialized bytes deterministic.

For D1/D2 components, identify sources of nondeterminism, including:

- unordered collections;
- concurrency scheduling;
- random values;
- timestamps;
- filesystem ordering;
- locale/timezone;
- environment-dependent behavior;
- floating-point accumulation order;
- encoder metadata.

The relevant determinism property MUST have a regression test.

## 9. Compatibility obligations

Any change to an existing public API, persisted representation, or externally consumed behavior requires an explicit compatibility review.

Review:

- positional calls;
- keyword calls;
- defaults;
- field order;
- return types;
- exceptions;
- serialized form;
- catalog membership;
- legacy behavior.

If compatibility is intentionally broken, the contract MUST state:

- what breaks;
- why;
- migration behavior;
- test coverage;
- release impact.

A passing new test suite does not establish compatibility.

## 10. Security and provenance obligations

For R3/R4 external or workflow boundaries:

- untrusted input is validated before entering domain logic;
- executable-looking strings remain inert unless an explicit execution contract exists;
- dynamic execution is prohibited unless separately contracted and reviewed;
- provenance is declarative;
- external resources are not implicitly downloaded or discovered.

Security tests MUST target both the intended safe path and hostile-looking inputs.

## 11. Resource and ownership obligations

Any component that acquires resources MUST document:

- owner;
- admission condition;
- reservation;
- lifetime;
- release;
- duplicate-release behavior;
- wrong-owner behavior;
- cleanup failure behavior.

The lifecycle MUST be observable in tests.

Do not use implementation size as a substitute for an ownership proof.

## 12. Complexity as a sizing signal

LOC MAY be reviewed as a diagnostic signal.

Suspicious patterns include:

- a high-risk component with almost no negative tests;
- a public boundary with no compatibility tests;
- a resource owner with no failure-path cleanup test;
- a serializer with no malformed-input tests;
- a state machine with no invalid-transition tests;
- a security boundary with only happy-path tests.

The correct response is to identify the missing proof obligation, not to add arbitrary lines.

## 13. Test/code ratio policy

A test/code ratio MAY be tracked for engineering visibility.

It MUST NOT be:

- a merge gate;
- a definition of quality;
- a reason to add artificial tests;
- a reason to inflate implementation code.

A low ratio is a signal to ask why important invariants are not tested.

A high ratio is a signal to ask whether tests are redundant, not proof that the project is safer.

## 14. Minimum documentation obligations

Every R2+ component MUST have enough documentation to answer:

- what is the contract?
- what are the invariants?
- who owns the state/resources?
- what mutations are permitted?
- what happens on failure?
- what happens on cancellation?
- what is deterministic?
- what is compatible?
- what is explicitly out of scope?

Critical R4 components MUST have a threat/failure model and an explicit residual-risk statement.

## 15. Proof-of-completeness checklist

Before declaring a component complete, the reviewer MUST be able to point to:

- contract;
- invariant list;
- applicable risk level;
- direct tests for invariants;
- adversarial tests;
- compatibility tests if applicable;
- determinism tests if applicable;
- ownership/resource tests if applicable;
- failure injection where applicable;
- security tests where applicable;
- local verification;
- CI evidence;
- CodeQL/security evidence;
- adversarial review;
- residual risks.

If one required proof obligation is missing, the component is not complete.

## 16. Anti-overengineering rule

This standard MUST NOT be interpreted as a requirement to add:

- generic abstractions;
- registries;
- plugin frameworks;
- state machines where a simple state model is sufficient;
- property-based tests where a small exhaustive set is stronger;
- fault-injection infrastructure before a meaningful failure boundary exists;
- extra layers solely to increase code size.

The smallest architecture that completely satisfies the contract is preferred.

## 17. Project-wide survival principle

Ai GIF Studio is considered robust only when critical behavior is supported by evidence, not by implementation size.

The governing equation is:

**Robustness evidence = contract coverage + invariant coverage + adversarial coverage + failure semantics + compatibility + determinism + ownership correctness + security evidence + exact-commit verification**

No single metric replaces this evidence.

## 18. Required workflow for every future phase

Every future phase MUST use:

**Contract -> invariants -> risk classification -> adversarial tests -> minimal implementation -> local compile/lint/tests -> CI -> CodeQL/security -> adversarial review -> compatibility/architecture review -> merge -> post-merge verification**

Any deviation requires an explicit documented reason.

## Final sizing rule

Do not ask:

> How many lines should this component contain?

Ask:

> What must be true, how can it fail, how can I try to break it, and what evidence proves that it survives those failures?

That question determines the required engineering depth.
