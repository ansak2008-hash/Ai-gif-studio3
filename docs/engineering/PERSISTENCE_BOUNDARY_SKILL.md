# Persistence Boundary Engineering Skill

## Purpose
A repeatable contract-first workflow for implementing and reviewing persistence boundaries without coupling domain code to storage.

## Gates
1. Contract: define schema version, exact fields, deterministic ordering, integrity rules, encoding rules, byte/object limits, invalid-input behavior, and non-goals.
2. Tests: cover deterministic output, round-trip, insertion-order independence, duplicate keys, non-finite numbers, malformed JSON, schema mismatch, missing root/current, orphan parents, duplicate identities, corrupted identities, invalid types, limits, immutability, and non-canonical input.
3. Implementation: keep the boundary pure; enforce byte limits before parsing; reject duplicate keys and non-finite numbers; reconstruct only after validation; re-encode and compare canonical bytes; use immutable graph snapshots; preserve domain identity contracts.
4. Adversarial review: check exception containment, bounded traversal, early limit enforcement, root/current integrity, Unicode byte limits, mutation safety, and absence of storage dependencies in the domain.
5. Verification: targeted tests, full unit suite, integration, determinism, Ruff, security checks, CodeQL, then final adversarial review.

## Change Discipline
- Fix incorrect tests rather than weakening a correct API.
- Prefer a small explicit public boundary over private-state coupling.
- Do not introduce registries, plugins, generic serializers, or framework abstractions without repeated concrete need.
- Crash-safe atomic writes, recovery, migrations, encryption, compression, and concrete storage adapters require their own contracts unless explicitly included.

## Exit Criteria
The boundary is complete only when the canonical document is deterministic, bounded, integrity-checked, round-trip safe, storage-agnostic, and verified by CI and CodeQL.
